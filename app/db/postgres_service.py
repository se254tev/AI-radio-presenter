"""Postgres Service - asyncpg connection pool wrapper for Supabase/Postgres
"""
import asyncio
import logging
from typing import Any

import asyncpg

from app.config.settings import CONFIG

logger = logging.getLogger(__name__)


class PostgresService:
    """Simple async Postgres service using asyncpg pool."""

    def __init__(self, dsn: str | None = None, min_size: int = 1, max_size: int = 10):
        self.dsn = dsn or CONFIG.database.database_url
        self.min_size = min_size
        self.max_size = max_size
        self.pool: asyncpg.pool.Pool | None = None

    async def initialize(self, retries: int = 3, delay: float = 2.0) -> None:
        attempt = 0
        while attempt < retries:
            try:
                self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=self.min_size, max_size=self.max_size)
                logger.info("Postgres pool created")
                return
            except Exception as e:
                attempt += 1
                logger.error(f"Postgres init failed (attempt {attempt}): {e}")
                await asyncio.sleep(delay)
        raise RuntimeError("Failed to initialize Postgres pool")

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            logger.info("Postgres pool closed")

    async def execute(self, query: str, *args, timeout: float | None = None) -> str:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    # Convenience CRUD helpers (simple implementations)
    async def insert(self, table: str, data: dict[str, Any]) -> Any:
        keys = ", ".join(data.keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(data)))
        query = f"INSERT INTO {table} ({keys}) VALUES ({placeholders}) RETURNING *"
        values = list(data.values())
        return await self.fetchrow(query, *values)

    async def select(self, table: str, where: str = "", params: list[Any] | None = None) -> list[asyncpg.Record]:
        query = f"SELECT * FROM {table}"
        if where:
            query += f" WHERE {where}"
        return await self.fetch(query, *(params or []))

    async def update(self, table: str, set_clause: str, where: str = "", params: list[Any] | None = None) -> Any:
        query = f"UPDATE {table} SET {set_clause}"
        if where:
            query += f" WHERE {where}"
        return await self.execute(query, *(params or []))

    async def delete(self, table: str, where: str = "", params: list[Any] | None = None) -> Any:
        query = f"DELETE FROM {table}"
        if where:
            query += f" WHERE {where}"
        return await self.execute(query, *(params or []))


postgres_service = PostgresService()
