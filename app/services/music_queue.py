"""
Music Queue Service - Queue management with Redis or in-memory fallback
"""
import logging
from typing import Optional, List, Dict, Any
import json
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class MusicQueue:
    """
    Redis-backed or in-memory music queue for managing track playback
    """

    def __init__(self, redis_client: Optional[Any] = None, max_queue_size: int = 500):
        self.redis = redis_client
        self.max_queue = max_queue_size
        # In-memory fallback queue
        self._local_queue: List[Dict[str, Any]] = []
        self._current_track: Optional[Dict[str, Any]] = None
        self._queue_name = "radio:queue"
        self._current_key = "radio:current_track"

    async def initialize(self) -> None:
        """Initialize queue storage"""
        if self.redis:
            try:
                # Test Redis connection
                await self.redis.ping()
                logger.info("Music queue using Redis backend")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}; using in-memory queue")
                self.redis = None
        else:
            logger.info("Music queue using in-memory backend")

    async def add_track(self, track: Dict[str, Any]) -> bool:
        """Add track to queue"""
        try:
            if len(await self.get_queue_size()) >= self.max_queue:
                logger.warning("Queue is full")
                return False

            track_json = json.dumps(track)

            if self.redis:
                await self.redis.rpush(self._queue_name, track_json)
            else:
                self._local_queue.append(track)

            logger.debug(f"Track added: {track.get('title', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to add track: {e}")
            return False

    async def get_next_track(self) -> Optional[Dict[str, Any]]:
        """Get and remove next track from queue"""
        try:
            if self.redis:
                track_json = await self.redis.lpop(self._queue_name)
                if track_json:
                    track = json.loads(track_json)
                    self._current_track = track
                    await self.redis.set(
                        self._current_key, json.dumps(track)
                    )
                    return track
            else:
                if self._local_queue:
                    track = self._local_queue.pop(0)
                    self._current_track = track
                    return track

            logger.debug("Queue empty, returning None")
            return None
        except Exception as e:
            logger.error(f"Failed to get next track: {e}")
            return None

    async def peek_next(self) -> Optional[Dict[str, Any]]:
        """Peek at next track without removing"""
        try:
            if self.redis:
                track_json = await self.redis.lindex(self._queue_name, 0)
                if track_json:
                    return json.loads(track_json)
            else:
                if self._local_queue:
                    return self._local_queue[0]
            return None
        except Exception as e:
            logger.error(f"Failed to peek: {e}")
            return None

    async def get_current_track(self) -> Optional[Dict[str, Any]]:
        """Get currently playing track"""
        try:
            if self.redis:
                track_json = await self.redis.get(self._current_key)
                if track_json:
                    return json.loads(track_json)
            return self._current_track
        except Exception as e:
            logger.error(f"Failed to get current track: {e}")
            return None

    async def get_queue_size(self) -> int:
        """Get current queue length"""
        try:
            if self.redis:
                return await self.redis.llen(self._queue_name)
            return len(self._local_queue)
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0

    async def get_queue(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get queue contents (limited to prevent huge responses)"""
        try:
            limit = min(limit, 100)  # Cap at 100 items
            if self.redis:
                items = await self.redis.lrange(self._queue_name, 0, limit - 1)
                return [json.loads(item) for item in items]
            return self._local_queue[:limit]
        except Exception as e:
            logger.error(f"Failed to get queue: {e}")
            return []

    async def clear_queue(self) -> bool:
        """Clear the entire queue"""
        try:
            if self.redis:
                await self.redis.delete(self._queue_name)
            else:
                self._local_queue.clear()
            logger.info("Queue cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            return False

    async def get_status(self) -> Dict[str, Any]:
        """Return queue status"""
        return {
            "backend": "redis" if self.redis else "in-memory",
            "queue_size": await self.get_queue_size(),
            "max_size": self.max_queue,
            "current_track": await self.get_current_track(),
            "next_track": await self.peek_next(),
        }
