from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return the async Redis singleton, creating it lazily on first call."""
    global _redis
    if _redis is None:
        _redis = aioredis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Close the Redis connection and reset the singleton."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
