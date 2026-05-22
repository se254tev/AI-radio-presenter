"""
Redis service for async connection management with TLS support.
Uses redis.asyncio for async operations with rediss:// protocol for cloud endpoints.
"""

import asyncio
import logging

from app.config.settings import CONFIG

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class RedisService:
    """Async Redis connection manager with retry logic and TLS support."""

    def __init__(self, url: str | None = None):
        """
        Initialize Redis service.
        
        Args:
            url: Redis connection URL (e.g., rediss://user:pass@host:port)
                 If None, uses CONFIG.redis.redis_url
        """
        if not redis:
            logger.warning("redis[asyncio] not installed. Redis service will be disabled.")
        
        self.url = url or CONFIG.redis.redis_url
        self.client: redis.Redis | None = None

    async def initialize(self, retries: int = 3, delay: float = 1.5):
        """
        Connect to Redis with exponential backoff retry logic.
        
        Args:
            retries: Number of connection attempts
            delay: Initial delay between retries in seconds
        
        Raises:
            ConnectionError: If unable to connect after all retries
        """
        if not redis:
            logger.warning("Redis client not available. Skipping initialization.")
            return

        if not self.url:
            logger.warning("REDIS_URL not configured. Skipping Redis initialization.")
            return

        for attempt in range(retries):
            try:
                logger.info(f"Connecting to Redis (attempt {attempt + 1}/{retries})...")
                
                # Parse URL and create connection
                # rediss:// protocol enables TLS
                self.client = redis.from_url(
                    self.url,
                    decode_responses=True,
                    encoding="utf-8",
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )
                
                # Test connection with ping
                await self.client.ping()
                logger.info("Redis connection established successfully")
                return
                
            except (ConnectionError, TimeoutError, Exception) as e:
                logger.warning(
                    f"Redis connection failed (attempt {attempt + 1}/{retries}): {e}"
                )
                
                if attempt < retries - 1:
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to Redis after {retries} attempts")
                    raise ConnectionError(
                        f"Could not connect to Redis at {self.url}: {e}"
                    )

    async def close(self):
        """Close Redis connection."""
        if self.client:
            try:
                await self.client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    async def get(self, key: str) -> str | None:
        """Get value by key."""
        if not self.client:
            return None
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None

    async def set(self, key: str, value: str, ex: int | None = None):
        """
        Set key-value pair with optional expiration.
        
        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds (optional)
        """
        if not self.client:
            return False
        try:
            await self.client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key."""
        if not self.client:
            return False
        try:
            result = await self.client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            return False

    async def hget(self, name: str, key: str) -> str | None:
        """Get value from hash."""
        if not self.client:
            return None
        try:
            return await self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET error for hash '{name}', key '{key}': {e}")
            return None

    async def hset(self, name: str, key: str, value: str) -> bool:
        """Set value in hash."""
        if not self.client:
            return False
        try:
            await self.client.hset(name, key, value)
            return True
        except Exception as e:
            logger.error(f"Redis HSET error for hash '{name}': {e}")
            return False

    async def incr(self, key: str) -> int | None:
        """Increment counter."""
        if not self.client:
            return None
        try:
            return await self.client.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR error for key '{key}': {e}")
            return None

    async def ping(self) -> bool:
        """Test Redis connection."""
        if not self.client:
            return False
        try:
            result = await self.client.ping()
            return bool(result)
        except Exception as e:
            logger.error(f"Redis PING failed: {e}")
            return False


# Singleton instance
redis_service = RedisService()
