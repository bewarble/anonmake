from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import load_settings


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
