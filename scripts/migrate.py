from __future__ import annotations

import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.database.session import engine

CORE_TABLES = {"users", "questions", "answers"}
INITIAL_REVISION = "20260726_0001"


async def inspect_database() -> tuple[set[str], str | None]:
    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        )

        revision: str | None = None
        if "alembic_version" in tables:
            result = await connection.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            revision = result.scalar_one_or_none()

    return tables, revision


async def run_alembic(function, config: Config, revision: str) -> None:
    # Alembic's asynchronous env starts its own event loop. The synchronous
    # command API therefore runs in a worker thread.
    await asyncio.to_thread(function, config, revision)


async def main() -> None:
    config = Config("alembic.ini")
    tables, revision = await inspect_database()

    # Empty database: apply every migration normally.
    if not tables or tables == {"alembic_version"}:
        await run_alembic(command.upgrade, config, "head")
        print("Database upgraded to Alembic head.")
        return

    # Legacy Stage 3 database created before Alembic tracking existed.
    if CORE_TABLES.issubset(tables) and "alembic_version" not in tables:
        await run_alembic(command.stamp, config, INITIAL_REVISION)
        print(f"Legacy core schema stamped at {INITIAL_REVISION}.")
        await run_alembic(command.upgrade, config, "head")
        print("Database upgraded to Alembic head.")
        return

    # Normal case for all current and future revisions. Never hard-code the
    # current head and never stamp a tracked database backwards.
    if "alembic_version" in tables:
        await run_alembic(command.upgrade, config, "head")
        print(
            "Database upgraded to Alembic head"
            + (f" from {revision}." if revision else ".")
        )
        return

    raise RuntimeError(
        "Unrecognized database schema. "
        f"Existing tables: {sorted(tables)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
