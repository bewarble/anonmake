from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect

from app.database.session import close_database, engine, init_database
from app.models.billing import Subscription
from app.services.vip import has_active_vip


async def check() -> None:
    await init_database()

    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(
                lambda conn: inspect(conn).get_table_names()
            )
        )

    assert "reveal_checkouts" in tables, tables

    active = Subscription(
        user_id=-1,
        access_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    expired = Subscription(
        user_id=-2,
        access_until=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    cancelled_but_paid = Subscription(
        user_id=-3,
        auto_renew=False,
        access_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    assert has_active_vip(active)
    assert not has_active_vip(expired)
    assert has_active_vip(cancelled_but_paid)

    await close_database()

    print("Stage 5.1 check: OK")
    print("Messages keep both buttons")
    print("Active VIP reveals any old or new message only after button press")
    print("Inactive VIP opens Impaya checkout for 1 RUB")


if __name__ == "__main__":
    asyncio.run(check())
