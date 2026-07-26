import asyncio
from pathlib import Path

from sqlalchemy import text

from app.database.session import (
    DATABASE_PATH,
    SessionFactory,
    close_database,
    init_database,
)


async def check() -> None:
    await init_database()

    async with SessionFactory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1

    assert Path(DATABASE_PATH).exists()

    await close_database()

    print("Stage 2.1 check: OK")
    print(f"Database: {DATABASE_PATH}")


if __name__ == "__main__":
    asyncio.run(check())
