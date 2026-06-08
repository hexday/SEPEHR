"""
SEPEHR Backend — Redis Cache Infrastructure
"""

from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


class CacheClient:
    """High-level cache operations with JSON serialization."""

    def __init__(self, prefix: str = "sepehr") -> None:
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Any:
        redis = await get_redis()
        value = await redis.get(self._key(key))
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        redis = await get_redis()
        serialized = json.dumps(value)
        if ttl:
            await redis.setex(self._key(key), ttl, serialized)
        else:
            await redis.set(self._key(key), serialized)

    async def delete(self, key: str) -> None:
        redis = await get_redis()
        await redis.delete(self._key(key))

    async def delete_pattern(self, pattern: str) -> int:
        redis = await get_redis()
        keys = await redis.keys(self._key(pattern))
        if keys:
            return await redis.delete(*keys)
        return 0

    async def exists(self, key: str) -> bool:
        redis = await get_redis()
        return bool(await redis.exists(self._key(key)))

    async def expire(self, key: str, ttl: int) -> None:
        redis = await get_redis()
        await redis.expire(self._key(key), ttl)

    async def incr(self, key: str) -> int:
        redis = await get_redis()
        return await redis.incr(self._key(key))

    async def incr_by(self, key: str, amount: int) -> int:
        redis = await get_redis()
        return await redis.incrby(self._key(key), amount)

    async def ttl(self, key: str) -> int:
        redis = await get_redis()
        return await redis.ttl(self._key(key))


class RateLimiter:
    """Sliding window rate limiter using Redis."""

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis = redis_client

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis:
            return self._redis
        return await get_redis()

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if a request is allowed.
        Returns (allowed, remaining_count).
        Uses a simple counter with TTL strategy.
        """
        redis = await self._get_redis()
        rate_key = f"ratelimit:{key}"

        pipe = redis.pipeline()
        pipe.incr(rate_key)
        pipe.ttl(rate_key)
        results = await pipe.execute()

        count: int = results[0]
        ttl: int = results[1]

        if ttl == -1:  # Key exists but no TTL
            await redis.expire(rate_key, window_seconds)
        elif ttl == -2:  # Key was just created by incr
            await redis.expire(rate_key, window_seconds)

        allowed = count <= max_requests
        remaining = max(0, max_requests - count)
        return allowed, remaining


# ── Presence Tracking ─────────────────────────────────────────────────────────

class PresenceManager:
    """Track user online status via Redis."""

    PRESENCE_TTL = 120  # 2 minutes

    async def set_online(self, user_id: str) -> None:
        redis = await get_redis()
        await redis.setex(f"presence:{user_id}", self.PRESENCE_TTL, "1")

    async def set_offline(self, user_id: str) -> None:
        redis = await get_redis()
        await redis.delete(f"presence:{user_id}")

    async def is_online(self, user_id: str) -> bool:
        redis = await get_redis()
        return bool(await redis.exists(f"presence:{user_id}"))

    async def get_online_users(self, user_ids: list[str]) -> dict[str, bool]:
        if not user_ids:
            return {}
        redis = await get_redis()
        keys = [f"presence:{uid}" for uid in user_ids]
        results = await redis.mget(*keys)
        return {uid: (val is not None) for uid, val in zip(user_ids, results)}

    async def heartbeat(self, user_id: str) -> None:
        """Refresh presence TTL."""
        redis = await get_redis()
        await redis.expire(f"presence:{user_id}", self.PRESENCE_TTL)


cache = CacheClient()
rate_limiter = RateLimiter()
presence = PresenceManager()
