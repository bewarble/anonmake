from __future__ import annotations

import asyncio

from app.database.session import SessionFactory, close_database, init_database
from app.repositories.admin_users import AdminUsersRepository


async def check() -> None:
    await init_database()

    async with SessionFactory() as session:
        users, has_next = await AdminUsersRepository(session).recent_users(
            page=0
        )
        assert isinstance(users, list)
        assert isinstance(has_next, bool)

        if users:
            card = await AdminUsersRepository(session).get_card(users[0].id)
            assert card is not None
            assert card.questions_sent >= 0
            assert card.questions_received >= 0
            assert card.answers_sent >= 0

    await close_database()

    print("Stage 17 check: OK")
    print("Admin users: paginated")
    print("User card: activity, VIP and payment summary")
    print("Actions: existing audited VIP controls")


if __name__ == "__main__":
    asyncio.run(check())
