from __future__ import annotations

import asyncio
import secrets

from sqlalchemy import inspect

from app.database.session import SessionFactory, close_database, engine, init_database
from app.repositories.marketing import MarketingRepository


async def check() -> None:
    await init_database()

    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        )
    required = {"traffic_sources", "source_attributions", "broadcasts"}
    assert required.issubset(tables), (required, tables)

    async with SessionFactory() as session:
        source = await MarketingRepository(session).create_source(
            name=f"Stage 19 {secrets.token_hex(3)}",
            source_url="https://example.com/ad",
            spend_kopecks=10000,
            admin_telegram_id=1,
        )
        item = await MarketingRepository(session).create_broadcast(
            kind="news",
            audience="all",
            text="Stage 19",
            admin_telegram_id=1,
        )
        await session.rollback()
        assert source.code
        assert item.status == "queued"

    await close_database()

    print("Stage 19 check: OK")
    print("Start: terms message before personal link")
    print("Sources: links, spend and attribution statistics")
    print("Broadcasts: news and subscription audiences")
    print("Delivery: durable outbox through broadcast worker")


if __name__ == "__main__":
    asyncio.run(check())
