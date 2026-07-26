from __future__ import annotations

import asyncio
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.database.session import SessionFactory, close_database, engine
from scripts.migrate import main as migrate

EXPECTED_TABLES = {"users", "questions", "answers", "alembic_version"}


async def check() -> None:
    await migrate()
    async with engine.connect() as connection:
        tables = set(await connection.run_sync(lambda conn: inspect(conn).get_table_names()))
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables: {sorted(missing)}"

    async with SessionFactory() as session:
        assert (await session.execute(text("SELECT 1"))).scalar_one() == 1

    head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    assert head == "20260726_0001"
    assert Path("Dockerfile").exists()
    assert Path("compose.yaml").exists()
    await close_database()

    print("Stage 4.1 check: OK")
    print(f"Alembic head: {head}")
    print("Infrastructure: Docker + PostgreSQL ready")


if __name__ == "__main__":
    asyncio.run(check())
