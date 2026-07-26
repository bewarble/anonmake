from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class DependencyStatus:
    database: bool
    redis: bool

    @property
    def healthy(self) -> bool:
        return self.database and self.redis


async def check_dependencies(
    engine: AsyncEngine,
    redis: Redis,
) -> DependencyStatus:
    database_ok = False
    redis_ok = False

    try:
        async with engine.connect() as connection:
            database_ok = (await connection.scalar(text("SELECT 1"))) == 1
    except Exception:
        pass

    try:
        redis_ok = bool(await redis.ping())
    except Exception:
        pass

    return DependencyStatus(database=database_ok, redis=redis_ok)
