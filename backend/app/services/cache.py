"""TTL cache behind a small protocol: Redis when configured, in-memory otherwise."""

import json
import time
from typing import Any, Protocol

from app.config import get_settings


class Cache(Protocol):
    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...


class MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            self.misses += 1
            return None
        self.hits += 1
        return value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, value)


class RedisCache:
    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(url, decode_responses=True)  # type: ignore[no-untyped-call]
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Any | None:
        raw = await self._redis.get(key)
        if raw is None:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self._redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)


_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        settings = get_settings()
        _cache = RedisCache(settings.redis_url) if settings.redis_url else MemoryCache()
    return _cache


def reset_cache() -> None:
    global _cache
    _cache = None
