from __future__ import annotations

import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.database.session import engine

CORE_TABLES = {"users", "questions", "answers"}
BILLING_TABLES = {"payment_methods", "subscriptions", "payment_attempts"}
CORE_REVISION = "20260726_0001"
HEAD_REVISION = "20260726_0002"


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
    # Alembic's async env creates its own event loop, so execute its synchronous
    # command API in a worker thread instead of nesting asyncio.run().
    await asyncio.to_thread(function, config, revision)


async def main() -> None:
    config = Config("alembic.ini")
    tables, revision = await inspect_database()

    has_core = CORE_TABLES.issubset(tables)
    has_billing = BILLING_TABLES.issubset(tables)

    if not tables or tables == {"alembic_version"}:
        await run_alembic(command.upgrade, config, "head")
        print("Database upgraded to Alembic head.")
        return

    if has_core and not has_billing:
        # Existing MVP database, or a database incorrectly stamped at 0002 by
        # Stage 5.0. The physical schema is still revision 0001.
        if revision != CORE_REVISION:
            await run_alembic(command.stamp, config, CORE_REVISION)
            print(f"Core schema stamped at {CORE_REVISION}.")
        await run_alembic(command.upgrade, config, "head")
        print(f"Database upgraded from {CORE_REVISION} to {HEAD_REVISION}.")
        return

    if has_core and has_billing:
        if revision != HEAD_REVISION:
            await run_alembic(command.stamp, config, HEAD_REVISION)
            print(f"Complete billing schema stamped at {HEAD_REVISION}.")
        else:
            print("Database is already at Alembic head.")
        return

    missing_core = sorted(CORE_TABLES - tables)
    raise RuntimeError(
        "Unrecognized partial database schema. "
        f"Missing core tables: {missing_core}. Existing tables: {sorted(tables)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
