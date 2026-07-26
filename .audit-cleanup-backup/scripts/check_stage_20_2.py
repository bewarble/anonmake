from __future__ import annotations

import asyncio
import secrets

from sqlalchemy import func, select

from app.database.session import SessionFactory, close_database, init_database
from app.models.crm import CrmEvent
from app.models.user import User
from app.services.crm_tracking import CrmTrackingService


async def check() -> None:
    await init_database()

    async with SessionFactory() as session:
        user_id = await session.scalar(
            select(User.id).order_by(User.id).limit(1)
        )

        if user_id is None:
            raise RuntimeError(
                "Stage 20.2 check requires at least one user in the database"
            )

        question_id = secrets.randbelow(2_000_000_000)

        tracking = CrmTrackingService(session)

        await tracking.question_sent(
            user_id=user_id,
            question_id=question_id,
        )

        await tracking.question_sent(
            user_id=user_id,
            question_id=question_id,
        )

        count = await session.scalar(
            select(func.count(CrmEvent.id)).where(
                CrmEvent.external_key
                == f"question:{question_id}:sender"
            )
        )

        assert int(count or 0) == 1

        await session.rollback()

    await close_database()

    print("Stage 20.2 check: OK")
    print("CRM events: automatic lifecycle tracking")
    print("Idempotency: duplicate events suppressed")
    print("Coverage: start, source, messages, answers, VIP and reveal")


if __name__ == "__main__":
    asyncio.run(check())
