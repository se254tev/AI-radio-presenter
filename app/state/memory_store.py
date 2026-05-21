import asyncio
from typing import Dict, Optional, List


class MemoryStore:
    """Simple in-memory key/value store used as a persistence fallback."""

    def __init__(self):
        self._store: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            self._store[key] = value

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            return self._store.get(key)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def keys(self, prefix: str = "") -> List[str]:
        async with self._lock:
            return [key for key in self._store if key.startswith(prefix)]
