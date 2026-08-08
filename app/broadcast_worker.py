from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from html import escape
import logging
import os

from sqlalchemy import exists, select

from app.bot.keyboards.questions import answer_question_keyboard
from app.core import texts
from app.core.config import load_settings
from app.core.logging import configure_logging
from app.core.performance import WORKER_BATCHES, WORKER_BATCH_SIZE, WORKER_IDLE_SECONDS, next_idle_delay
from app.core.worker_health import mark_worker_heartbeat
from app.database.session import SessionFactory, close_database, init_database
from app.models.billing import Subscription
from app.models.marketing import Broadcast
from app.models.question import Question
from app.models.user import User
from app.repositories.delivery import DeliveryRepository
from app.repositories.marketing import MarketingRepository
from app.services.delivery import serialize_markup

logger = logging.getLogger(__name__)


async def audience_users(session, item, batch_size: int) -> list[User]:
    query = (
        select(User)
        .where(User.bot_id == item.bot_id, User.id > item.cursor_user_id)
        .order_by(User.id)
        .limit(batch_size)
    )

    now = datetime.now(timezone.utc)
    active_vip = exists(
        select(Subscription.id).where(
            Subscription.bot_id == item.bot_id,
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


async def configured_sender(session, telegram_id: int, bot_id: int) -> User:
    sender = await session.scalar(
        select(User).where(User.bot_id == bot_id, User.telegram_id == telegram_id)
    )
    if sender is None:
        raise RuntimeError("BROADCAST_SENDER_TELEGRAM_ID does not belong to this bot")
    return sender


async def enqueue_broadcast_batch(session, *, item, users: list[User], sender: User) -> None:
    delivery = DeliveryRepository(session)

    for recipient in users:
        question = Question(
            sender_id=sender.id,
            recipient_id=recipient.id,
            text=item.text,
            status="queued",
        )
        session.add(question)
        await session.flush()

        markup = answer_question_keyboard(question.id)
        await delivery.enqueue(
            kind="broadcast_question",
            dedupe_key=f"broadcast:{item.id}:user:{recipient.id}",
            bot_id=item.bot_id,
            chat_id=recipient.telegram_id,
            text=texts.NEW_QUESTION.format(text=escape(question.text)),
            reply_markup=serialize_markup(markup),
            payload={"parse_mode": "HTML"},
        )


async def mark_broadcast_failed(session, broadcast_id: int) -> None:
    item = await session.get(Broadcast, broadcast_id)
    if item is None:
        return
    item.status = "failed"
    item.completed_at = datetime.now(timezone.utc)
    await session.commit()


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.json_logs)
    await init_database()

    sender_telegram_id = settings.broadcast_sender_telegram_id
    if sender_telegram_id <= 0:
        raise RuntimeError("BROADCAST_SENDER_TELEGRAM_ID is missing or invalid")

    interval = float(os.getenv("BROADCAST_POLL_INTERVAL_SECONDS", "3"))
    batch_size = int(os.getenv("BROADCAST_BATCH_SIZE", "500"))
    idle_max = float(os.getenv("BROADCAST_IDLE_MAX_SECONDS", str(settings.worker_idle_max_seconds)))
    idle_delay = interval

    mark_worker_heartbeat("broadcast-worker", state="started")
    logger.info("Broadcast worker started")

    try:
        while True:
            try:
                mark_worker_heartbeat("broadcast-worker", state="polling")
                async with SessionFactory() as session:
                    repository = MarketingRepository(session)
                    item = await repository.next_broadcast()

                    if item is None:
                        await session.rollback()
                        WORKER_BATCHES.labels("broadcast", "empty").inc()
                        WORKER_IDLE_SECONDS.labels("broadcast").set(idle_delay)
                        mark_worker_heartbeat(
                            "broadcast-worker",
                            state="idle",
                            idle_seconds=idle_delay,
                        )
                        await asyncio.sleep(idle_delay)
                        idle_delay = next_idle_delay(idle_delay, interval, idle_max)
                        continue

                    item_id = item.id
                    item_bot_id = item.bot_id
                    idle_delay = interval
                    WORKER_IDLE_SECONDS.labels("broadcast").set(idle_delay)
                    mark_worker_heartbeat(
                        "broadcast-worker",
                        state="processing",
                        broadcast_id=item_id,
                        bot_id=item_bot_id,
                    )

                    try:
                        sender = await configured_sender(
                            session,
                            sender_telegram_id,
                            item_bot_id,
                        )
                        await repository.mark_broadcast_started(item)
                        users = await audience_users(session, item, batch_size)

                        if not users:
                            await repository.mark_broadcast_completed(item)
                            await session.commit()
                            mark_worker_heartbeat(
                                "broadcast-worker",
                                state="completed",
                                broadcast_id=item_id,
                            )
                            continue

                        await enqueue_broadcast_batch(
                            session,
                            item=item,
                            users=users,
                            sender=sender,
                        )
                        WORKER_BATCHES.labels("broadcast", "queued").inc()
                        WORKER_BATCH_SIZE.labels("broadcast").observe(len(users))

                        item.cursor_user_id = users[-1].id
                        item.queued_count += len(users)
                        await session.commit()
                        mark_worker_heartbeat(
                            "broadcast-worker",
                            state="processing",
                            broadcast_id=item_id,
                            queued_count=item.queued_count,
                        )
                    except Exception as exc:
                        await session.rollback()
                        try:
                            await mark_broadcast_failed(session, item_id)
                        except Exception:
                            await session.rollback()
                            logger.exception(
                                "Could not persist failed broadcast status broadcast_id=%s bot_id=%s",
                                item_id,
                                item_bot_id,
                            )
                        WORKER_BATCHES.labels("broadcast", "failed").inc()
                        mark_worker_heartbeat(
                            "broadcast-worker",
                            state="job_failed",
                            broadcast_id=item_id,
                            bot_id=item_bot_id,
                            exception_type=type(exc).__name__,
                        )
                        logger.exception(
                            "Broadcast processing failed broadcast_id=%s bot_id=%s",
                            item_id,
                            item_bot_id,
                        )
                        continue
            except Exception as exc:
                WORKER_BATCHES.labels("broadcast", "worker_error").inc()
                mark_worker_heartbeat(
                    "broadcast-worker",
                    state="error",
                    exception_type=type(exc).__name__,
                )
                logger.exception("Broadcast worker iteration failed")
                await asyncio.sleep(interval)
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
