"""MongoDB Service - Motor async client wrapper
Async MongoDB connection management with health checks
"""
import logging
from typing import Any
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from app.config.settings import CONFIG

logger = logging.getLogger(__name__)


class MongoService:
    """Async MongoDB connection manager with retry logic and health checks."""
    
    def __init__(self, uri: str | None = None, db_name: str | None = None):
        self.uri = uri or CONFIG.mongo.mongo_uri
        self.db_name = db_name or CONFIG.mongo.mongo_db
        self.client: AsyncIOMotorClient | None = None
        self.db = None
        self.healthy = False

    async def initialize(self, retries: int = 3, delay: float = 1.5) -> bool:
        """
        Connect to MongoDB with exponential backoff retry logic.
        
        Args:
            retries: Number of connection attempts
            delay: Initial delay between retries in seconds
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        attempt = 0
        while attempt < retries:
            try:
                logger.info(f"Connecting to MongoDB (attempt {attempt + 1}/{retries})...")
                self.client = AsyncIOMotorClient(
                    self.uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                )
                # Test connection with server_info()
                await asyncio.wait_for(self.client.server_info(), timeout=5.0)
                self.db = self.client[self.db_name]
                self.healthy = True
                logger.info(f"✅ MongoDB connected successfully to database '{self.db_name}'")
                return True
            except asyncio.TimeoutError:
                attempt += 1
                logger.warning(f"MongoDB connection timeout (attempt {attempt}/{retries})")
                if attempt < retries:
                    await asyncio.sleep(delay * (2 ** (attempt - 1)))  # Exponential backoff
            except Exception as e:
                attempt += 1
                logger.warning(f"MongoDB init failed (attempt {attempt}/{retries}): {type(e).__name__}: {e}")
                if attempt < retries:
                    await asyncio.sleep(delay * (2 ** (attempt - 1)))  # Exponential backoff
        
        self.healthy = False
        logger.error(f"❌ Failed to initialize MongoDB after {retries} attempts")
        return False

    async def health_check(self) -> bool:
        """Check if MongoDB connection is healthy."""
        try:
            if not self.client:
                self.healthy = False
                return False
            await asyncio.wait_for(self.client.server_info(), timeout=5.0)
            self.healthy = True
            return True
        except Exception as e:
            logger.warning(f"MongoDB health check failed: {e}")
            self.healthy = False
            return False

    async def close(self) -> None:
        """Close MongoDB connection."""
        try:
            if self.client:
                self.client.close()
                self.healthy = False
                logger.info("MongoDB client closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")

    async def insert_one(self, collection: str, document: dict[str, Any]) -> Any:
        """Insert a single document into collection."""
        try:
            if not self.db:
                raise RuntimeError("MongoDB not initialized")
            col = self.db[collection]
            result = await col.insert_one(document)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Failed to insert into {collection}: {e}")
            raise

    async def find(self, collection: str, filter: dict[str, Any], limit: int = 100) -> list[dict[str, Any]]:
        """Find documents in collection."""
        try:
            if not self.db:
                raise RuntimeError("MongoDB not initialized")
            col = self.db[collection]
            cursor = col.find(filter).limit(limit)
            return [doc async for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to find in {collection}: {e}")
            return []

    async def update_one(self, collection: str, filter: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """Update a single document in collection."""
        try:
            if not self.db:
                raise RuntimeError("MongoDB not initialized")
            col = self.db[collection]
            result = await col.update_one(filter, {"$set": update})
            return {"matched_count": result.matched_count, "modified_count": result.modified_count}
        except Exception as e:
            logger.error(f"Failed to update in {collection}: {e}")
            raise

    async def delete_one(self, collection: str, filter: dict[str, Any]) -> dict[str, Any]:
        """Delete a single document from collection."""
        try:
            if not self.db:
                raise RuntimeError("MongoDB not initialized")
            col = self.db[collection]
            result = await col.delete_one(filter)
            return {"deleted_count": result.deleted_count}
        except Exception as e:
            logger.error(f"Failed to delete in {collection}: {e}")
            raise


mongo_service = MongoService()
