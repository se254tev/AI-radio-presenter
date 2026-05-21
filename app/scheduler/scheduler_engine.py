import asyncio
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Any


class SchedulerEngine:
    """External timing engine for scheduled starts and runtime segment waits."""

    def __init__(self):
        self.scheduled_tasks: Dict[str, asyncio.Task] = {}

    async def wait(self, duration_seconds: float) -> None:
        """Wait for a duration without blocking the event loop."""
        await asyncio.sleep(max(0.0, duration_seconds))

    async def schedule(self, task_id: str, start_time: datetime, callback: Callable[..., Any]) -> None:
        """Schedule a callback to execute at a future datetime."""
        delay = (start_time - datetime.utcnow()).total_seconds()
        if delay < 0:
            delay = 0.0

        async def _delayed_start():
            await asyncio.sleep(delay)
            await callback()

        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id].cancel()

        self.scheduled_tasks[task_id] = asyncio.create_task(_delayed_start())

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled start task."""
        task = self.scheduled_tasks.pop(task_id, None)
        if task and not task.done():
            task.cancel()
            return True
        return False
