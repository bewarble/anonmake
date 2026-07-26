from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.database.session import SessionFactory, close_database


async def main() -> None:
    try:
        async with SessionFactory() as session:
            value = (await session.execute(text("SELECT 1"))).scalar_one()
            if value != 1:
                raise RuntimeError("Unexpected database healthcheck response")
        print("Healthcheck: OK")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
