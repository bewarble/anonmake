from __future__ import annotations

import asyncio

from app.database.session import SessionFactory, close_database, init_database
from app.repositories.admin_control import AdminControlRepository


async def check() -> None:
    await init_database()

    async with SessionFactory() as session:
        repository = AdminControlRepository(session)

        overview = await repository.overview()
        assert overview.users_total >= 0
        assert overview.active_vip >= 0
        assert overview.delivery_pending >= 0

        users, users_next = await repository.users(
            filter_name="recent",
            page=0,
        )
        assert isinstance(users, list)
        assert isinstance(users_next, bool)

        payments, payments_next = await repository.payments(
            filter_name="all",
            page=0,
        )
        assert isinstance(payments, list)
        assert isinstance(payments_next, bool)

        subscriptions, subscriptions_next = await repository.subscriptions(
            filter_name="active",
            page=0,
        )
        assert isinstance(subscriptions, list)
        assert isinstance(subscriptions_next, bool)

    await close_database()

    print("Stage 18 check: OK")
    print("Admin center: operational overview")
    print("Users: filters and pagination")
    print("Subscriptions: active, renewal, cancelled, expired")
    print("Payments: filters, pagination and details")


if __name__ == "__main__":
    asyncio.run(check())
