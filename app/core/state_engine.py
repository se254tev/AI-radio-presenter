"""
State Engine - Persistent Runtime Memory System
Handles show state, timing, and segment tracking
Supports Redis with in-memory fallback
"""
import json
import logging
import asyncio
from typing import Any

from app.config.settings import CONFIG
from app.models.show import ShowPlan
from app.models.state import (
    ShowState,
    SegmentExecution,
    SegmentStatus,
    AudienceMetrics,
    BroadcastStatus,
)
from app.state.memory_store import MemoryStore

logger = logging.getLogger(__name__)


class StateEngine:
    """
    Manages persistent application state
    Supports Redis (preferred) with in-memory fallback
    """

    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis and CONFIG.redis.enable
        self.redis_client = None  # Will be set via redis_service singleton
        self.memory_store = MemoryStore()
        self._lock = asyncio.Lock()

    def set_redis_client(self, redis_client):
        """Set the redis client from redis_service singleton (called during app initialization)."""
        self.redis_client = redis_client
        if self.redis_client:
            logger.info("Redis client initialized for state engine")
            self.use_redis = True
        else:
            logger.warning("Redis client not available; using in-memory fallback")
            self.use_redis = False

    async def save_state(self, state: ShowState) -> bool:
        async with self._lock:
            try:
                payload = json.dumps(state.to_dict())
                key = f"show_state:{state.show_id}"
                if self.redis_client:
                    await self.redis_client.setex(key, 86400, payload)
                    return True
                await self.memory_store.set(key, payload)
                return True
            except Exception as exc:
                logger.error(f"Failed to save state for {state.show_id}: {exc}")
                return False

    async def load_state(self, show_id: str) -> ShowState | None:
        async with self._lock:
            try:
                key = f"show_state:{show_id}"
                payload = None
                if self.redis_client:
                    payload = await self.redis_client.get(key)
                if payload is None:
                    payload = await self.memory_store.get(key)
                if not payload:
                    return None
                return ShowState.from_dict(json.loads(payload))
            except Exception as exc:
                logger.error(f"Failed to load state for {show_id}: {exc}")
                return None

    async def delete_state(self, show_id: str) -> bool:
        async with self._lock:
            try:
                key = f"show_state:{show_id}"
                if self.redis_client:
                    await self.redis_client.delete(key)
                await self.memory_store.delete(key)
                return True
            except Exception as exc:
                logger.error(f"Failed to delete state for {show_id}: {exc}")
                return False

    async def list_active_shows(self) -> list[str]:
        async with self._lock:
            try:
                if self.redis_client:
                    keys = await self.redis_client.keys("show_state:*")
                    return [key.replace("show_state:", "") for key in keys]
                keys = await self.memory_store.keys("show_state:")
                return [key.replace("show_state:", "") for key in keys]
            except Exception as exc:
                logger.error(f"Failed to list active shows: {exc}")
                return []

    async def save_show_plan(self, show_plan: ShowPlan) -> bool:
        async with self._lock:
            try:
                payload = json.dumps(show_plan.to_dict())
                key = f"show_plan:{show_plan.show_id}"
                if self.redis_client:
                    await self.redis_client.setex(key, 86400, payload)
                    return True
                await self.memory_store.set(key, payload)
                return True
            except Exception as exc:
                logger.error(f"Failed to save show plan {show_plan.show_id}: {exc}")
                return False

    async def load_show_plan(self, show_id: str) -> ShowPlan | None:
        async with self._lock:
            try:
                key = f"show_plan:{show_id}"
                payload = None
                if self.redis_client:
                    payload = await self.redis_client.get(key)
                if payload is None:
                    payload = await self.memory_store.get(key)
                if not payload:
                    return None
                return ShowPlan.from_dict(json.loads(payload))
            except Exception as exc:
                logger.error(f"Failed to load show plan {show_id}: {exc}")
                return None

    async def close(self) -> None:
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis client closed")


state_engine = StateEngine(use_redis=True)
