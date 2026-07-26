from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import inspect, select

from app.database.session import SessionFactory, close_database, engine, init_database
from app.models.billing import PaymentAttempt, PaymentMethod, Subscription


async def check() -> None:
    await init_database()
    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        )
    expected = {"payment_methods", "subscriptions", "payment_attempts"}
    assert expected.issubset(tables), (expected, tables)

    async with SessionFactory() as session:
        result = await session.execute(select(Subscription).limit(1))
        result.scalars().first()
        await session.rollback()

    await close_database()
    print("Stage 5 check: OK")
    print("Billing tables: payment_methods, subscriptions, payment_attempts")
    print("Renewal policy: 299 RUB / 3 days -> 99 RUB / 1 day -> retry next day")


if __name__ == "__main__":
    asyncio.run(check())
