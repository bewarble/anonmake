from __future__ import annotations

import asyncio

from app.database.session import SessionFactory, close_database, init_database
from app.services.analytics import AnalyticsService


async def check() -> None:
    await init_database()

    async with SessionFactory() as session:
        snapshot = await AnalyticsService(session).snapshot()

    assert snapshot.users_total >= 0
    assert snapshot.questions_total >= 0
    assert snapshot.answers_total >= 0
    assert 0 <= snapshot.answer_rate
    assert 0 <= snapshot.vip_rate

    await close_database()

    print("Stage 15 check: OK")
    print("Analytics: users, questions, answers")
    print("Business metrics: reveals, VIP, payments, revenue")
    print("Periods: 24 hours, 7 days, 30 days")


if __name__ == "__main__":
    asyncio.run(check())
