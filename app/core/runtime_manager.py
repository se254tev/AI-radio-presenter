import asyncio
import logging
from datetime import datetime
from typing import Any

from .broadcast_loop import BroadcastLoop
from .state_engine import StateEngine
from .show_planner import ShowPlanner, ShowPlan
from ..ai.llm_generator import get_llm_generator
from ..voice.tts_engine import get_tts_engine
from ..scheduler.scheduler_engine import SchedulerEngine
from ..streaming.stream_manager import StreamManager

logger = logging.getLogger(__name__)


class RuntimeManager:
    """Core controller for show lifecycle, scheduling, and runtime orchestration."""

    def __init__(
        self,
        state_engine: StateEngine,
        scheduler_engine: SchedulerEngine,
        stream_manager: StreamManager,
    ):
        self.state_engine = state_engine
        self.scheduler_engine = scheduler_engine
        self.stream_manager = stream_manager
        self.llm_generator = get_llm_generator()
        self.tts_engine = get_tts_engine()
        self.show_planner = ShowPlanner()
        self.active_runs: dict[str, BroadcastLoop] = {}
        self.logger = logging.getLogger(__name__)

    async def start_show(self, show_plan: ShowPlan) -> str:
        """Start a show immediately."""
        show_state = await self.state_engine.load_state(show_plan.show_id)
        if show_state and show_state.status in [show_state.status.RUNNING, show_state.status.PAUSED]:
            raise RuntimeError(f"Show {show_plan.show_id} is already active")

        broadcast = BroadcastLoop(
            show_plan=show_plan,
            state_engine=self.state_engine,
        )

        self.active_runs[show_plan.show_id] = broadcast
        started = await broadcast.start_broadcast()
        if not started:
            self.active_runs.pop(show_plan.show_id, None)
            raise RuntimeError(f"Failed to start show {show_plan.show_id}")

        self.logger.info(f"Started show {show_plan.show_id}")
        return show_plan.show_id

    async def schedule_show(self, show_plan: ShowPlan, start_time: datetime) -> str:
        """Schedule a show to start at a future time."""
        show_plan.planned_start_time = start_time
        await self.state_engine.save_show_plan(show_plan)

        async def _start():
            try:
                await self.start_show(show_plan)
                self.logger.info(f"Scheduled show {show_plan.show_id} started")
            except Exception as exc:
                self.logger.error(f"Scheduled start failed for {show_plan.show_id}: {exc}")

        await self.scheduler_engine.schedule(show_plan.show_id, start_time, _start)
        return show_plan.show_id

    async def stop_show(self, show_id: str) -> bool:
        broadcast = self.active_runs.get(show_id)
        if broadcast:
            success = await broadcast.stop_broadcast()
            if success:
                self.active_runs.pop(show_id, None)
            return success

        canceled = self.scheduler_engine.cancel(show_id)
        if canceled:
            return True

        return False

    async def pause_show(self, show_id: str) -> bool:
        broadcast = self.active_runs.get(show_id)
        if not broadcast:
            return False
        return await broadcast.pause_broadcast()

    async def resume_show(self, show_id: str) -> bool:
        broadcast = self.active_runs.get(show_id)
        if not broadcast:
            return False
        return await broadcast.resume_broadcast()

    async def get_show_state(self, show_id: str) -> dict[str, Any | None]:
        if show_id in self.active_runs:
            return self.active_runs[show_id].get_status()
        show_state = await self.state_engine.load_state(show_id)
        if not show_state:
            return None
        return {
            "show_id": show_state.show_id,
            "show_name": show_state.show_name,
            "status": show_state.status.value,
            "elapsed_time": show_state.elapsed_time,
            "remaining_time": show_state.remaining_time,
            "current_segment_index": show_state.current_segment_index,
            "total_segments": show_state.total_segments,
            "segments_completed": show_state.segments_completed,
            "energy_level": show_state.energy_level,
            "language": show_state.current_language,
        }

    async def get_show_history(self, show_id: str) -> dict[str, Any | None]:
        show_state = await self.state_engine.load_state(show_id)
        if not show_state:
            return None
        return {
            "show_id": show_state.show_id,
            "show_name": show_state.show_name,
            "status": show_state.status.value,
            "segment_history": [segment.to_dict() for segment in show_state.segment_history],
            "audience_metrics": show_state.audience_metrics.to_dict(),
        }

    async def list_active_shows(self) -> dict[str, Any]:
        return {
            show_id: broadcast.get_status()
            for show_id, broadcast in self.active_runs.items()
        }
