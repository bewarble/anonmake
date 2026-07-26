from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os

from sqlalchemy import exists, select

from app.core.config import load_settings
from app.core.logging import configure_logging
from app.database.session import SessionFactory, close_database, init_database
from app.models.billing import Subscription
from app.models.user import User
from app.repositories.delivery import DeliveryRepository
from app.repositories.marketing import MarketingRepository

logger = logging.getLogger(__name__)


async def audience_users(session, item, batch_size: int):
    query = (
        select(User)
        .where(User.id > item.cursor_user_id)
        .order_by(User.id)
        .limit(batch_size)
    )

    now = datetime.now(timezone.utc)
    active_vip = exists(
        select(Subscription.id).where(
            Subscription.user_id == User.id,
            Subscription.access_until.is_not(None),
            Subscription.access_until > now,
        )
    )

    if item.audience == "vip":
        query = query.where(active_vip)
    elif item.audience == "non_vip":
        query = query.where(~active_vip)

    result = await session.execute(query)
    return list(result.scalars())


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.json_logs)
    await init_database()

    interval = float(os.getenv("BROADCAST_POLL_INTERVAL_SECONDS", "3"))
    batch_size = int(os.getenv("BROADCAST_BATCH_SIZE", "500"))

    logger.info("Broadcast worker started")

    try:
        while True:
            async with SessionFactory() as session:
                repository = MarketingRepository(session)
                item = await repository.next_broadcast()
                if item is None:
                    await session.rollback()
                    await asyncio.sleep(interval)
                    continue

                await repository.mark_broadcast_started(item)
                users = await audience_users(session, item, batch_size)

                if not users:
                    await repository.mark_broadcast_completed(item)
                    await session.commit()
                    continue

                delivery = DeliveryRepository(session)
                for user in users:
                    await delivery.enqueue(
                        kind="broadcast",
                        dedupe_key=f"broadcast:{item.id}:user:{user.id}",
                        chat_id=user.telegram_id,
                        text=item.text,
                    )

                item.cursor_user_id = users[-1].id
                item.queued_count += len(users)
                await session.commit()
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
