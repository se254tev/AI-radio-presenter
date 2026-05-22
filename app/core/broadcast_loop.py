"""
Broadcast Loop - Core Runtime Engine
Main autonomous broadcast execution engine
Orchestrates: Timing, Director decisions, LLM generation, TTS, and State management
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from enum import Enum

from .show_planner import ShowPlan, SegmentType
from .state_engine import (
    StateEngine,
    ShowState,
    SegmentExecution,
    SegmentStatus,
    BroadcastStatus,
)
from .director import Director, DirectorDecision
from ..ai.llm_generator import (
    get_llm_generator,
    SegmentPromptContext,
    LLMGenerator,
)
from ..voice.tts_engine import get_tts_engine, TTSEngine, AudioOutput
from app.services.music_queue import MusicQueue
from app.streaming.websocket import ws_manager
import json

logger = logging.getLogger(__name__)


class BroadcastLoopEvent(str, Enum):
    """Events emitted by broadcast loop"""
    SEGMENT_START = "segment_start"
    SEGMENT_COMPLETE = "segment_complete"
    CONTENT_GENERATED = "content_generated"
    AUDIO_READY = "audio_ready"
    DIRECTOR_DECISION = "director_decision"
    STATE_UPDATE = "state_update"
    ERROR = "error"
    BROADCAST_COMPLETE = "broadcast_complete"


class BroadcastLoop:
    """
    Core broadcast execution engine
    Runs the continuous autonomous broadcast loop
    
    Loop Flow:
    1. Read current state
    2. Get Director decision
    3. Execute decision (move segment, adjust timing, etc.)
    4. Generate segment content (LLM)
    5. Convert to speech (TTS)
    6. Stream/play audio
    7. Update state
    8. Wait for next segment
    9. Repeat until show ends
    """
    
    def __init__(
        self,
        show_plan: ShowPlan,
        state_engine: StateEngine,
        event_callback: Optional[Callable] = None,
    ):
        """
        Initialize broadcast loop
        
        Args:
            show_plan: The show plan to execute
            state_engine: State engine for persistence
            event_callback: Optional async callback for events
        """
        self.show_plan = show_plan
        self.state_engine = state_engine
        self.event_callback = event_callback
        self.director = Director(show_plan)
        self.llm_generator = get_llm_generator()
        self.tts_engine = get_tts_engine()
        self.music_queue = MusicQueue()
        self.music_queue.event_callback = self._on_music_event
        
        self.state: Optional[ShowState] = None
        self.is_running = False
        self.is_paused = False
        self.logger = logging.getLogger(__name__)
        
        self.loop_task: Optional[asyncio.Task] = None
    
    async def initialize_show(self) -> ShowState:
        """
        Initialize show state before broadcast starts
        
        Returns:
            ShowState: Initialized show state
        """
        self.state = ShowState(
            show_id=self.show_plan.show_id,
            show_name=self.show_plan.show_name,
            planned_duration=self.show_plan.total_duration,
            status=BroadcastStatus.STARTING,
            current_segment_index=0,
            total_segments=len(self.show_plan.segments),
            primary_language=self.show_plan.primary_language,
            secondary_language=self.show_plan.secondary_language,
            current_language=self.show_plan.primary_language,
            energy_level=0.7,
            humor_level=0.3,
            language_mix_level=0.2,
        )
        
        await self.state_engine.save_state(self.state)
        self.logger.info(f"Show initialized: {self.show_plan.show_name}")
        await self._emit_event(BroadcastLoopEvent.STATE_UPDATE, self.state.to_dict())
        
        return self.state
    
    async def start_broadcast(self) -> bool:
        """
        Start autonomous broadcast execution
        
        Returns:
            bool: True if started successfully
        """
        try:
            if not self.state:
                await self.initialize_show()
            
            self.state.status = BroadcastStatus.RUNNING
            self.state.start_time = datetime.utcnow()
            self.is_running = True
            
            await self.state_engine.save_state(self.state)
            
            self.logger.info(f"Broadcast started: {self.show_plan.show_name}")
            await self._emit_event(BroadcastLoopEvent.SEGMENT_START, {"show_id": self.state.show_id})
            
            # Start main broadcast loop
            # Initialize music queue
            try:
                await self.music_queue.initialize()
            except Exception:
                pass

            self.loop_task = asyncio.create_task(self._main_loop())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start broadcast: {e}")
            self.state.status = BroadcastStatus.FAILED
            await self.state_engine.save_state(self.state)
            await self._emit_event(BroadcastLoopEvent.ERROR, {"error": str(e)})
            return False
    
    async def stop_broadcast(self) -> bool:
        """Stop broadcast execution"""
        try:
            self.is_running = False
            
            if self.loop_task:
                self.loop_task.cancel()
                try:
                    await self.loop_task
                except asyncio.CancelledError:
                    pass
            
            self.state.status = BroadcastStatus.STOPPED
            self.state.end_time = datetime.utcnow()
            await self.state_engine.save_state(self.state)
            
            self.logger.info("Broadcast stopped by user")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping broadcast: {e}")
            return False
    
    async def pause_broadcast(self) -> bool:
        """Pause broadcast execution"""
        if not self.is_running:
            return False
        
        self.is_paused = True
        self.state.status = BroadcastStatus.PAUSED
        await self.state_engine.save_state(self.state)
        self.logger.info("Broadcast paused")
        return True
    
    async def resume_broadcast(self) -> bool:
        """Resume paused broadcast"""
        if not self.is_running or not self.is_paused:
            return False
        
        self.is_paused = False
        self.state.status = BroadcastStatus.RUNNING
        await self.state_engine.save_state(self.state)
        self.logger.info("Broadcast resumed")
        return True
    
    async def _main_loop(self):
        """
        Main broadcast execution loop
        Runs continuously until show ends
        """
        self.logger.info("Entering main broadcast loop")
        
        try:
            # Continuous radio loop: alternate music and short AI speech
            last_track_id = None
            while self.is_running:
                # Handle pause
                while self.is_paused and self.is_running:
                    await asyncio.sleep(0.5)

                if not self.is_running:
                    break

                # Update timing
                self.state.update_timing()

                # End show when time's up
                if self.state.remaining_time <= 0:
                    self.logger.info("Show duration reached - ending broadcast")
                    await self._finish_broadcast()
                    break

                # Ask director what to do next (async)
                try:
                    director_decision = await self.director.decide_next_action(self.state)
                    await self._emit_event(
                        BroadcastLoopEvent.DIRECTOR_DECISION,
                        {
                            "decision": director_decision.decision.value,
                            "reason": director_decision.reason,
                        }
                    )
                except Exception as e:
                    self.logger.debug(f"Director decision error: {e}")
                    director_decision = None

                # Ensure music is playing by default
                current_track = await self.music_queue.ensure_playing()

                # If track changed, broadcast track_play
                track_id = current_track.get("id") if current_track else None
                if track_id and track_id != last_track_id:
                    last_track_id = track_id
                    await ws_manager.broadcast_event("music", {"event": "track_play", "track": current_track})

                # Check director decision
                if director_decision and director_decision.decision in (
                    DirectorDecision.AI_SPEECH,
                    DirectorDecision.RESPOND_TO_LISTENER,
                    DirectorDecision.ANNOUNCEMENT,
                ):
                    # Pause music (simulated) and run AI speech
                    await self._handle_ai_interruption(director_decision, current_track)
                    # After speech, always resume music
                    await ws_manager.broadcast_event("music", {"event": "resume_music", "track": current_track})
                    await asyncio.sleep(0.5)
                    continue

                # Default: play through track duration but check periodically for interrupts
                duration = int(current_track.get("duration", 30))
                elapsed = 0
                check_interval = 2
                while elapsed < duration and self.is_running and not self.is_paused:
                    await asyncio.sleep(min(check_interval, duration - elapsed))
                    elapsed += min(check_interval, duration - elapsed)
                    # Periodically re-check director for quick interruptions
                    try:
                        dd = await self.director.decide_next_action(self.state)
                        if dd.decision in (DirectorDecision.AI_SPEECH, DirectorDecision.RESPOND_TO_LISTENER):
                            director_decision = dd
                            break
                    except Exception:
                        pass

                # After track completes naturally, auto-advance
                if self.is_running:
                    await self.music_queue.play_next()
                await asyncio.sleep(0.1)
        
        except asyncio.CancelledError:
            self.logger.info("Broadcast loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in main broadcast loop: {e}")
            self.state.status = BroadcastStatus.FAILED
            await self._emit_event(BroadcastLoopEvent.ERROR, {"error": str(e)})
        finally:
            await self.state_engine.save_state(self.state)

    async def _on_music_event(self, event_type: str, payload: Dict[str, Any]):
        """Forward music queue events to websocket manager in unified format."""
        try:
            await ws_manager.broadcast_event("music", {"event": event_type, **(payload or {})})
        except Exception:
            pass
    
    async def _start_next_segment(self):
        """Start execution of next segment"""
        try:
            current_segment = self.state.current_segment()
            next_index = self.state.current_segment_index
            
            if current_segment and current_segment.status == SegmentStatus.COMPLETED:
                next_index += 1
            
            if next_index >= len(self.show_plan.segments):
                await self._finish_broadcast()
                return
            
            segment_def = self.show_plan.segments[next_index]
            
            # Create execution record
            segment_exec = SegmentExecution(
                segment_id=segment_def.segment_id,
                segment_type=segment_def.segment_type.value,
                status=SegmentStatus.ACTIVE,
                planned_duration=segment_def.duration,
                language=segment_def.language,
                mood=segment_def.mood.value,
                start_time=datetime.utcnow(),
            )
            
            self.state.current_segment_index = next_index
            self.state.add_segment_record(segment_exec)
            
            self.logger.info(
                f"Starting segment {next_index + 1}/{len(self.show_plan.segments)}: "
                f"{segment_def.title}"
            )
            
            await self._emit_event(
                BroadcastLoopEvent.SEGMENT_START,
                {
                    "segment_index": next_index,
                    "segment_id": segment_def.segment_id,
                    "segment_title": segment_def.title,
                    "segment_type": segment_def.segment_type.value,
                    "duration": segment_def.duration,
                }
            )
            
            # Generate content and audio
            await self._generate_and_synthesize_segment(segment_def, segment_exec)
            
            await self.state_engine.save_state(self.state)
            
        except Exception as e:
            self.logger.error(f"Error starting next segment: {e}")
            await self._emit_event(BroadcastLoopEvent.ERROR, {"error": str(e)})
    
    async def _generate_and_synthesize_segment(
        self,
        segment_def,
        segment_exec: SegmentExecution,
    ):
        """
        Generate content for segment and synthesize to speech
        Main LLM and TTS integration point
        """
        try:
            # Update audience metrics
            self.state.audience_metrics = self.director.simulate_audience_metrics(self.state)
            
            # Build LLM context
            context = SegmentPromptContext(
                segment_type=segment_def.segment_type.value,
                segment_title=segment_def.title,
                duration_seconds=segment_def.duration,
                language=segment_def.language,
                mood=segment_def.mood.value,
                humor_level=self.state.humor_level,
                energy_level=self.state.energy_level,
                audience_size=self.state.audience_metrics.listener_count,
                recent_topics=[s.segment_type for s in self.state.get_recent_context(3)],
                host_personality=self.show_plan.metadata.get("host_personality", "friendly, knowledgeable"),
                target_audience=self.show_plan.target_audience,
                code_switching_enabled=self.show_plan.code_switching_enabled,
            )
            
            # Generate script
            self.logger.debug(f"Generating script for {segment_def.title}")
            script = await self.llm_generator.generate_segment_script(context)
            segment_exec.content_hash = hash(script.content) % (10 ** 8)
            
            await self._emit_event(
                BroadcastLoopEvent.CONTENT_GENERATED,
                {
                    "segment_id": segment_def.segment_id,
                    "word_count": len(script.content.split()),
                    "estimated_duration": script.duration_estimate,
                }
            )
            
            # Synthesize to speech
            self.logger.debug(f"Synthesizing audio for {segment_def.title}")
            audio = await self.tts_engine.generate_audio(
                segment_id=segment_def.segment_id,
                text=script.content,
                language=segment_def.language,
                mood=segment_def.mood.value,
                duration_estimate=segment_def.duration,
            )
            
            segment_exec.audio_url = f"s3://radio-ai/audio/{segment_def.segment_id}.mp3"
            
            await self._emit_event(
                BroadcastLoopEvent.AUDIO_READY,
                {
                    "segment_id": segment_def.segment_id,
                    "audio_size_bytes": len(audio.audio_data),
                    "duration": audio.duration_seconds,
                }
            )
            
            # In production, stream/play audio here
            self.logger.info(
                f"Audio ready for {segment_def.title}: "
                f"{len(audio.audio_data)} bytes"
            )
            
        except Exception as e:
            self.logger.error(f"Error generating/synthesizing segment: {e}")
            segment_exec.status = SegmentStatus.ERROR
            segment_exec.error = str(e)
            await self._emit_event(BroadcastLoopEvent.ERROR, {"error": str(e)})
    
    async def _execute_director_decision(self, decision):
        """Execute director decision"""
        try:
            if decision.decision == DirectorDecision.PROCEED_TO_NEXT:
                # Already handled in main loop
                pass
            
            elif decision.decision == DirectorDecision.EXTEND_CURRENT:
                current = self.state.current_segment()
                if current:
                    current.planned_duration = int(current.planned_duration * decision.adjustment_value)
                    self.logger.info(f"Extended segment to {current.planned_duration}s")
            
            elif decision.decision == DirectorDecision.SHORTEN_CURRENT:
                current = self.state.current_segment()
                if current:
                    current.planned_duration = int(current.planned_duration * decision.adjustment_value)
                    self.logger.info(f"Shortened segment to {current.planned_duration}s")
            
            elif decision.decision == DirectorDecision.ADJUST_ENERGY:
                self.state.energy_level = max(0.0, min(1.0, 
                    self.state.energy_level + decision.adjustment_value
                ))
                self.logger.info(f"Adjusted energy to {self.state.energy_level:.2f}")
            
            elif decision.decision == DirectorDecision.SWITCH_LANGUAGE:
                old_lang = self.state.current_language
                self.state.current_language = "swahili" if old_lang == "english" else "english"
                self.logger.info(f"Switched language: {old_lang} -> {self.state.current_language}")
            
            elif decision.decision == DirectorDecision.SKIP_SEGMENT:
                self.state.current_segment_index += 1
                self.logger.info("Skipped optional segment")
            
            elif decision.decision == DirectorDecision.EMERGENCY_STOP:
                self.is_running = False
                self.logger.info("Emergency stop triggered by director")
        
        except Exception as e:
            self.logger.error(f"Error executing director decision: {e}")

    async def _handle_ai_interruption(self, decision, current_track):
        """Generate short AI speech, synthesize, broadcast, and wait for playback to finish."""
        try:
            # Build context for AI using recent chats from websocket manager
            recent = ws_manager.get_recent_chats(5)
            listener_messages = [m.get("text") for m in recent]

            segment_type = "music_block"
            if decision.decision == DirectorDecision.RESPOND_TO_LISTENER:
                segment_type = "listener_interaction"
            elif decision.decision == DirectorDecision.ANNOUNCEMENT:
                segment_type = "announcement"

            mood_str = "calm"
            if self.state.energy_level >= 0.75:
                mood_str = "hype"
            elif self.state.energy_level >= 0.4:
                mood_str = "talkative"

            context = SegmentPromptContext(
                segment_type=segment_type,
                segment_title=f"DJ_{segment_type}",
                duration_seconds=20,
                language=self.state.current_language,
                mood=mood_str,
                humor_level=self.state.humor_level,
                energy_level=self.state.energy_level,
                audience_size=getattr(self.state, 'audience_metrics', {}).listener_count if hasattr(self.state, 'audience_metrics') else 0,
                recent_topics=[s.segment_type for s in self.state.get_recent_context(3)] if hasattr(self.state, 'get_recent_context') else [],
                host_personality=self.show_plan.metadata.get("host_personality", "energetic, friendly"),
                target_audience=self.show_plan.target_audience,
                code_switching_enabled=self.show_plan.code_switching_enabled,
                listener_messages=listener_messages,
                current_song=current_track,
            )

            # Generate short DJ line (structured)
            dj_output = await self.llm_generator.generate_dj_line(context)

            text_out = dj_output.get("text", "")
            intent = dj_output.get("intent", "speech")
            emotion = dj_output.get("emotion", "calm")

            # Synthesize
            audio = await self.tts_engine.generate_audio(
                segment_id=context.segment_title,
                text=text_out,
                language=context.language,
                mood=emotion,
                duration_estimate=10,
            )

            # Broadcast AI speech event
            await ws_manager.broadcast_event("ai_speech", {
                "text": text_out,
                "audio_url": audio.audio_url,
                "duration": audio.duration_seconds,
                "intent": intent,
                "emotion": emotion,
            })

            # Wait for playback to finish (non-blocking sleep)
            await asyncio.sleep(audio.duration_seconds)

        except Exception as e:
            self.logger.error(f"AI interruption failed: {e}")
    
    async def _get_segment_elapsed_time(self, segment: SegmentExecution) -> int:
        """Get elapsed time for current segment"""
        if not segment or not segment.start_time:
            return 0
        return int((datetime.utcnow() - segment.start_time).total_seconds())
    
    async def _finish_broadcast(self):
        """Complete broadcast execution"""
        self.is_running = False
        self.state.status = BroadcastStatus.COMPLETED
        self.state.end_time = datetime.utcnow()
        
        await self.state_engine.save_state(self.state)
        
        self.logger.info(
            f"Broadcast completed: {self.state.show_name} "
            f"({self.state.elapsed_time}s elapsed)"
        )
        
        await self._emit_event(
            BroadcastLoopEvent.BROADCAST_COMPLETE,
            {
                "show_id": self.state.show_id,
                "segments_completed": self.state.segments_completed,
                "elapsed_time": self.state.elapsed_time,
            }
        )
    
    async def _emit_event(self, event_type: BroadcastLoopEvent, data: Dict[str, Any]):
        """Emit broadcast event"""
        if self.event_callback:
            try:
                await self.event_callback(event_type, data)
            except Exception as e:
                self.logger.error(f"Error in event callback: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current broadcast status"""
        if not self.state:
            return {"status": "not_initialized"}
        
        current_segment = self.state.current_segment()
        
        return {
            "show_id": self.state.show_id,
            "show_name": self.state.show_name,
            "status": self.state.status.value,
            "elapsed_time": self.state.elapsed_time,
            "remaining_time": self.state.remaining_time,
            "current_segment_index": self.state.current_segment_index,
            "total_segments": self.state.total_segments,
            "segments_completed": self.state.segments_completed,
            "energy_level": self.state.energy_level,
            "audience_metrics": self.state.audience_metrics.to_dict(),
            "current_segment": current_segment.to_dict() if current_segment else None,
        }
