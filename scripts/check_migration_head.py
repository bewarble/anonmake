from __future__ import annotations

import asyncio

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.database.session import close_database, engine, init_database


async def check() -> None:
    await init_database()

    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())

    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        )
        assert "alembic_version" in tables, tables

        result = await connection.execute(
            text("SELECT version_num FROM alembic_version")
        )
        actual_heads = set(result.scalars())

    assert actual_heads == expected_heads, (actual_heads, expected_heads)
    await close_database()

    print("Migration head check: OK")
    print("Alembic heads:", ", ".join(sorted(actual_heads)))


if __name__ == "__main__":
    asyncio.run(check())
