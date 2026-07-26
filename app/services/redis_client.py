from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis


@lru_cache(maxsize=4)
def get_redis(url: str) -> Redis:
    """Return one shared async Redis client per URL."""

    return Redis.from_url(
        url,
        decode_responses=True,
        health_check_interval=30,
        socket_connect_timeout=3,
        socket_timeout=3,
        retry_on_timeout=True,
    )
