from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import text

from app.database.session import SessionFactory, close_database

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "backups" / "deploy"
MAGIC = b"PGDMP"


def check_routes() -> None:
    import app.web.app

    paths = {
        route.path
        for route in app.web.app.app.routes
        if hasattr(route, "path")
    }
    assert "/admin/platform/system" in paths
    assert "/admin/platform/observability" in paths


def check_backups() -> None:
    if not BACKUP_DIR.exists():
        print("Stage 49 runtime: backup directory is not mounted; skipping dump check")
        return

    dumps = sorted(
        BACKUP_DIR.glob("*.dump"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not dumps:
        print("Stage 49 runtime: no deploy backups yet")
        return

    latest = dumps[0]
    with latest.open("rb") as stream:
        assert stream.read(len(MAGIC)) == MAGIC, latest
    assert latest.stat().st_size > len(MAGIC), latest
    print("Stage 49 runtime: latest backup format OK:", latest.name)


async def check_database() -> None:
    try:
        async with SessionFactory() as session:
            value = await session.scalar(text("SELECT 1"))
            assert value == 1
    finally:
        await close_database()


async def main() -> None:
    check_routes()
    check_backups()
    await check_database()
    print("Stage 49 runtime check: OK")


if __name__ == "__main__":
    asyncio.run(main())
