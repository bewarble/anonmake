from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.base import Base

DATABASE_PATH = Path("data/anonmake.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH.as_posix()}"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_database() -> None:
    """Create the data directory and all currently registered tables."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Import models before create_all so SQLAlchemy knows their metadata.
    import app.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session and always close it afterwards."""
    async with SessionFactory() as session:
        yield session


async def close_database() -> None:
    """Dispose of the SQLAlchemy connection pool."""
    await engine.dispose()
