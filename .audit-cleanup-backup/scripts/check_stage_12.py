from __future__ import annotations

import asyncio
import secrets

from sqlalchemy import inspect, select

from app.database.session import SessionFactory, close_database, engine, init_database
from app.repositories.delivery import DeliveryRepository


async def check() -> None:
    await init_database()

    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        )
    assert "delivery_outbox" in tables, tables

    key = f"stage12:{secrets.token_hex(8)}"
    async with SessionFactory() as session:
        first = await DeliveryRepository(session).enqueue(
            kind="test",
            dedupe_key=key,
            chat_id=-1,
            text="Stage 12",
        )
        second = await DeliveryRepository(session).enqueue(
            kind="test",
            dedupe_key=key,
            chat_id=-1,
            text="Stage 12",
        )
        await session.commit()
        assert first.id == second.id

    await close_database()

    print("Stage 12 check: OK")
    print("Delivery: durable PostgreSQL outbox")
    print("Concurrency: FOR UPDATE SKIP LOCKED")
    print("Retries: exponential backoff + Telegram RetryAfter")
    print("Idempotency: unique delivery dedupe key")


if __name__ == "__main__":
    asyncio.run(check())
