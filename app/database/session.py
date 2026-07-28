from __future__ import annotations

from pathlib import Path
import time

from sqlalchemy import event

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import load_settings
from app.core.performance import record_sql


settings = load_settings()
DATABASE_URL = settings.database_url
DATABASE_PATH: Path | None = None

if DATABASE_URL.startswith("sqlite+aiosqlite:///"):
    DATABASE_PATH = Path(DATABASE_URL.removeprefix("sqlite+aiosqlite:///"))

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=settings.sql_echo,
    pool_pre_ping=True,
)
SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_database() -> None:
    """Prepare local storage. Schema changes are managed by Alembic."""
    if DATABASE_PATH is not None:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


async def close_database() -> None:
    await engine.dispose()


if settings.performance_enabled:
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _before_cursor_execute(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        conn.info.setdefault("anonmake_query_started", []).append(
            time.perf_counter()
        )


    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _after_cursor_execute(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        stack = conn.info.get("anonmake_query_started") or []
        if not stack:
            return
        started = stack.pop()
        record_sql(
            statement,
            time.perf_counter() - started,
            slow_ms=settings.performance_slow_sql_ms,
        )
