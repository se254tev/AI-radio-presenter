"""MongoDB Service - Motor async client wrapper
"""
import logging
from typing import Any, Dict, List, Optional
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from app.config.settings import CONFIG

logger = logging.getLogger(__name__)


class MongoService:
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        self.uri = uri or CONFIG.mongo.mongo_uri
        self.db_name = db_name or CONFIG.mongo.mongo_db
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def initialize(self, retries: int = 3, delay: float = 1.5) -> None:
        attempt = 0
        while attempt < retries:
            try:
                self.client = AsyncIOMotorClient(self.uri)
                # Simple call to ensure connection
                await self.client.server_info()
                self.db = self.client[self.db_name]
                logger.info("MongoDB connected")
                return
            except Exception as e:
                attempt += 1
                logger.error(f"MongoDB init failed (attempt {attempt}): {e}")
                await asyncio.sleep(delay)
        raise RuntimeError("Failed to initialize MongoDB client")

    async def close(self) -> None:
        if self.client:
            self.client.close()
            logger.info("MongoDB client closed")

    async def insert_one(self, collection: str, document: Dict[str, Any]) -> Any:
        col = self.db[collection]
        result = await col.insert_one(document)
        return result.inserted_id

    async def find(self, collection: str, filter: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        col = self.db[collection]
        cursor = col.find(filter).limit(limit)
        return [doc async for doc in cursor]

    async def update_one(self, collection: str, filter: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        col = self.db[collection]
        result = await col.update_one(filter, {"$set": update})
        return {"matched_count": result.matched_count, "modified_count": result.modified_count}

    async def delete_one(self, collection: str, filter: Dict[str, Any]) -> Dict[str, Any]:
        col = self.db[collection]
        result = await col.delete_one(filter)
        return {"deleted_count": result.deleted_count}


mongo_service = MongoService()
