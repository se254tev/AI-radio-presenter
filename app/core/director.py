"""
Director System - Autonomous Decision Making Engine
Controls show flow, segment transitions, pacing, and content insertion
Completely separate from content generation (LLM)
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

from .show_planner import Segment, SegmentType, ShowPlan
from .state_engine import ShowState, SegmentStatus, AudienceMetrics

logger = logging.getLogger(__name__)


class DirectorDecision(str, Enum):
    """Types of director decisions"""
    PROCEED_TO_NEXT = "proceed_to_next"
    EXTEND_CURRENT = "extend_current"
    SHORTEN_CURRENT = "shorten_current"
    INSERT_BREAK = "insert_break"
    SKIP_SEGMENT = "skip_segment"
    ADJUST_ENERGY = "adjust_energy"
    SWITCH_LANGUAGE = "switch_language"
    PAUSE = "pause"
    RESUME = "resume"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class DirectorCommand:
    """Director command to be executed by broadcast loop"""
    decision: DirectorDecision
    reason: str
    target_segment: Optional[str] = None  # Segment ID to apply to
    adjustment_value: float = 0.0  # For energy, duration adjustments
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


class Director:
    """
    Autonomous show director
    Makes real-time decisions about:
    - Segment transitions
    - Pacing adjustments
    - Energy management
    - Content insertion/skipping
    - Language switching
    
    Does NOT generate content - only orchestrates flow
    """
    
    # Thresholds and parameters
    LOW_ENERGY_THRESHOLD = 0.3
    HIGH_ENERGY_THRESHOLD = 0.7
    ENGAGEMENT_THRESHOLD = 0.4
    
    EXTEND_RATIO = 1.2  # Can extend by 20%
    SHORTEN_RATIO = 0.8  # Can shorten to 80%
    
    def __init__(self, show_plan: ShowPlan):
        """
        Initialize director with show plan
        
        Args:
            show_plan: The show plan that defines structure
        """
        self.show_plan = show_plan
        self.logger = logging.getLogger(__name__)
        self.decision_history: List[DirectorCommand] = []
    
    def decide_next_action(self, state: ShowState) -> DirectorCommand:
        """
        Main decision-making function
        Analyzes current state and generates next action
        
        Args:
            state: Current broadcast state
        
        Returns:
            DirectorCommand: Next action to execute
        """
        # Check for emergency conditions
        if state.remaining_time <= 0:
            return self._make_command(
                DirectorDecision.EMERGENCY_STOP,
                "Show duration reached",
            )
        
        current_segment = state.current_segment()
        
        # If no current segment, start first
        if not current_segment:
            if state.current_segment_index == 0:
                return self._make_command(
                    DirectorDecision.PROCEED_TO_NEXT,
                    "Starting broadcast",
                )
            else:
                return self._make_command(
                    DirectorDecision.EMERGENCY_STOP,
                    "Invalid segment index",
                )
        
        # Check if current segment is completed
        if current_segment.status == SegmentStatus.COMPLETED:
            return self._decide_segment_transition(state)
        
        # Check if current segment needs adjustment
        adjustment = self._check_segment_adjustment(state, current_segment)
        if adjustment:
            return adjustment
        
        # Check energy levels
        energy_adjustment = self._check_energy_adjustment(state)
        if energy_adjustment:
            return energy_adjustment
        
        # Check language switching
        language_switch = self._check_language_switch(state)
        if language_switch:
            return language_switch
        
        # No action needed - continue current segment
        return self._make_command(
            DirectorDecision.PROCEED_TO_NEXT,  # Actually continue
            "Current segment running smoothly",
        )
    
    def _decide_segment_transition(self, state: ShowState) -> DirectorCommand:
        """
        Decide what to do after current segment completes
        - Move to next segment
        - Skip if optional
        - Insert filler/ad
        """
        next_index = state.current_segment_index + 1
        
        # Check if show is ending
        if next_index >= len(self.show_plan.segments):
            return self._make_command(
                DirectorDecision.EMERGENCY_STOP,
                "All segments completed",
            )
        
        next_segment = self.show_plan.segments[next_index]
        
        # Decide whether to proceed or skip
        if next_segment.optional and self._should_skip_segment(state, next_segment):
            return self._make_command(
                DirectorDecision.SKIP_SEGMENT,
                f"Skipping optional segment: {next_segment.title}",
                target_segment=next_segment.segment_id,
            )
        
        # Proceed to next segment
        return self._make_command(
            DirectorDecision.PROCEED_TO_NEXT,
            f"Moving to segment: {next_segment.title}",
            target_segment=next_segment.segment_id,
        )
    
    def _check_segment_adjustment(
        self,
        state: ShowState,
        current_segment: 'SegmentExecution'
    ) -> Optional[DirectorCommand]:
        """
        Check if current segment should be extended/shortened
        based on engagement and time remaining
        """
        if not current_segment or not current_segment.start_time:
            return None
        
        elapsed = (datetime.utcnow() - current_segment.start_time).total_seconds()
        remaining_in_segment = current_segment.planned_duration - elapsed
        
        # Check if we're running out of time
        if state.remaining_time < 600:  # Less than 10 minutes left
            if remaining_in_segment > 60:  # Current segment has time
                return self._make_command(
                    DirectorDecision.SHORTEN_CURRENT,
                    "Reducing segment - show time running out",
                    adjustment_value=0.8,
                )
        
        # Check audience engagement
        if state.audience_metrics.engagement_rate < self.ENGAGEMENT_THRESHOLD:
            if current_segment.segment_type != SegmentType.INTRO:
                return self._make_command(
                    DirectorDecision.SHORTEN_CURRENT,
                    "Low engagement - moving along",
                    adjustment_value=0.8,
                )
        
        return None
    
    def _check_energy_adjustment(self, state: ShowState) -> Optional[DirectorCommand]:
        """
        Check if energy level needs adjustment
        - Inject high-energy segments if dropping
        - Cool down if too high
        """
        if state.energy_level < self.LOW_ENERGY_THRESHOLD:
            return self._make_command(
                DirectorDecision.ADJUST_ENERGY,
                "Energy level low - injecting boost",
                adjustment_value=0.3,
            )
        
        if state.energy_level > self.HIGH_ENERGY_THRESHOLD:
            # Could insert calmer segment
            if state.remaining_time > 600:
                return self._make_command(
                    DirectorDecision.INSERT_BREAK,
                    "Energy too high - inserting breather",
                )
        
        return None
    
    def _check_language_switch(self, state: ShowState) -> Optional[DirectorCommand]:
        """
        Decide on language switching based on context and rules
        """
        # Don't switch too frequently
        if len(state.segment_history) < 2:
            return None
        
        recent_segments = state.get_recent_context(lookback_segments=2)
        
        # Strategy: Switch language based on content type and humor level
        current_lang = state.current_language
        next_lang = None
        
        if state.humor_level > 0.6:
            # Mix languages during high humor
            if current_lang == "english":
                next_lang = "swahili"
            else:
                next_lang = "english"
        
        # Check if sentiment shift warrants language change
        if state.audience_metrics.sentiment == "positive":
            if current_lang == "english":
                next_lang = "swahili"  # Emotional connection
        
        if next_lang and next_lang != current_lang:
            return self._make_command(
                DirectorDecision.SWITCH_LANGUAGE,
                f"Switching to {next_lang}",
                adjustment_value=0.0,
            )
        
        return None
    
    def _should_skip_segment(self, state: ShowState, segment: Segment) -> bool:
        """
        Determine if optional segment should be skipped
        based on remaining time and engagement
        """
        if not segment.optional:
            return False
        
        time_needed = sum(
            s.duration for s in self.show_plan.segments[
                state.current_segment_index+1:
            ]
        )
        
        # Skip if we don't have time
        if time_needed > state.remaining_time:
            return True
        
        return False
    
    def _make_command(
        self,
        decision: DirectorDecision,
        reason: str,
        target_segment: str = None,
        adjustment_value: float = 0.0,
    ) -> DirectorCommand:
        """Helper to create and log director command"""
        command = DirectorCommand(
            decision=decision,
            reason=reason,
            target_segment=target_segment,
            adjustment_value=adjustment_value,
            metadata={},
            timestamp=datetime.utcnow(),
        )
        
        self.decision_history.append(command)
        logger.info(f"Director: {decision.value} - {reason}")
        
        return command
    
    def simulate_audience_metrics(self, state: ShowState) -> AudienceMetrics:
        """
        Simulate realistic audience metrics based on segment and history
        In production, this would be replaced with real data
        """
        # Default metrics
        energy = 0.5
        engagement = 0.5
        sentiment = "neutral"
        
        current_segment = state.current_segment()
        if current_segment:
            # Adjust based on segment type
            if current_segment.segment_type == SegmentType.INTRO:
                energy = 0.8
                engagement = 0.7
            elif current_segment.segment_type == SegmentType.MUSIC_BLOCK:
                energy = 0.6
                engagement = 0.6
            elif current_segment.segment_type == SegmentType.TALK_SEGMENT:
                energy = 0.5
                engagement = 0.7
            elif current_segment.segment_type == SegmentType.LISTENER_INTERACTION:
                energy = 0.8
                engagement = 0.9
                sentiment = "positive"
            elif current_segment.segment_type == SegmentType.JOKE_BREAK:
                energy = 0.9
                sentiment = "positive"
        
        # Add some variation based on time
        elapsed_ratio = state.elapsed_time / max(state.planned_duration, 1)
        if elapsed_ratio > 0.7:  # Fatigue factor in last 30%
            energy *= 0.8
            engagement *= 0.85
        
        metrics = AudienceMetrics(
            energy_level=min(1.0, max(0.0, energy)),
            engagement_rate=min(1.0, max(0.0, engagement)),
            sentiment=sentiment,
            listener_count=int(1000 + (engagement * 500)),
        )
        
        return metrics
    
    def get_decision_summary(self) -> Dict[str, Any]:
        """Get summary of all decisions made"""
        return {
            "total_decisions": len(self.decision_history),
            "decisions_by_type": self._count_decisions(),
            "recent_decisions": [
                {
                    "decision": d.decision.value,
                    "reason": d.reason,
                    "timestamp": d.timestamp.isoformat(),
                }
                for d in self.decision_history[-10:]
            ],
        }
    
    def _count_decisions(self) -> Dict[str, int]:
        """Count decisions by type"""
        counts = {}
        for cmd in self.decision_history:
            decision_type = cmd.decision.value
            counts[decision_type] = counts.get(decision_type, 0) + 1
        return counts
