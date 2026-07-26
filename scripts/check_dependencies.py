from __future__ import annotations

import asyncio

from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import load_settings
from app.database.session import close_database, engine


async def main() -> None:
    settings = load_settings()

    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT 1")) == 1

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        assert await redis.ping()
    finally:
        await redis.aclose()

    await close_database()
    print("Dependency check: OK")
    print("PostgreSQL: available")
    print("Redis: available")


if __name__ == "__main__":
    asyncio.run(main())
