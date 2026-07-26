from __future__ import annotations

import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database.session import engine, init_database

EXPECTED_TABLES = {"users", "questions", "answers"}


async def database_state() -> tuple[set[str], bool]:
    await init_database()
    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(
                lambda conn: inspect(conn).get_table_names()
            )
        )
    return tables, "alembic_version" in tables


async def main() -> None:
    tables, has_version = await database_state()
    config = Config("alembic.ini")

    # Alembic's async env starts its own event loop. Run the synchronous
    # Alembic command in a worker thread so it is never nested inside the
    # application's currently running asyncio loop.
    if not has_version and EXPECTED_TABLES.issubset(tables):
        await asyncio.to_thread(command.stamp, config, "head")
        print("Existing Stage 3 schema stamped at Alembic head.")
    else:
        await asyncio.to_thread(command.upgrade, config, "head")
        print("Database upgraded to Alembic head.")


if __name__ == "__main__":
    asyncio.run(main())
