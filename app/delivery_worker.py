from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os
import socket
import uuid

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from sqlalchemy import select

from app.core.config import load_settings
from app.core.error_diagnostics import new_error_id, record_bot_error
from app.core.logging import configure_logging
from app.core.performance import WORKER_BATCHES, WORKER_BATCH_SIZE, WORKER_IDLE_SECONDS, next_idle_delay
from app.core.worker_health import mark_worker_heartbeat
from app.database.session import SessionFactory, close_database, init_database
from app.models.bot_instance import BotInstance
from app.models.user import User
from app.repositories.delivery import DeliveryRepository
from app.services.bot_pool import BotPool
from app.services.delivery import deserialize_markup

logger = logging.getLogger(__name__)

PERMANENT_BLOCK_MARKERS = (
    "bot was blocked",
    "chat not found",
    "user is deactivated",
)


def retry_delay(attempt: int) -> int:
    return min(300, 2 ** min(attempt + 1, 8))


def is_permanent_user_block(error: str) -> bool:
    lowered = error.lower()
    return any(marker in lowered for marker in PERMANENT_BLOCK_MARKERS)


async def mark_user_blocked_fallback(session, job, error: str) -> None:
    if not is_permanent_user_block(error):
        return
    user = await session.scalar(
        select(User).where(
            User.bot_id == job.bot_id,
            User.telegram_id == job.chat_id,
        )
    )
    if user is None:
        return
    user.is_blocked = True
    user.blocked_at = datetime.now(timezone.utc)


async def send_delivery(bot: Bot, job):
    markup = deserialize_markup(job.reply_markup)
    payload = job.payload or {}
    content_type = payload.get("content_type", "text")
    file_id = payload.get("file_id")
    caption = payload.get("caption") or job.text
    parse_mode = payload.get("parse_mode")

    if content_type == "text" or not file_id:
        return await bot.send_message(
            chat_id=job.chat_id,
            text=job.text,
            reply_markup=markup,
            parse_mode=parse_mode,
        )

    common = {
        "chat_id": job.chat_id,
        "reply_markup": markup,
        "parse_mode": parse_mode,
    }
    if content_type == "photo":
        return await bot.send_photo(photo=file_id, caption=caption, **common)
    if content_type == "video":
        return await bot.send_video(video=file_id, caption=caption, **common)
    if content_type == "document":
        return await bot.send_document(document=file_id, caption=caption, **common)
    if content_type == "animation":
        return await bot.send_animation(animation=file_id, caption=caption, **common)
    if content_type == "audio":
        return await bot.send_audio(audio=file_id, caption=caption, **common)
    if content_type == "voice":
        return await bot.send_voice(voice=file_id, caption=caption, **common)
    if content_type == "video_note":
        return await bot.send_video_note(
            chat_id=job.chat_id,
            video_note=file_id,
            reply_markup=markup,
        )
    if content_type == "sticker":
        return await bot.send_sticker(
            chat_id=job.chat_id,
            sticker=file_id,
            reply_markup=markup,
        )

    return await bot.send_message(
        chat_id=job.chat_id,
        text=job.text,
        reply_markup=markup,
        parse_mode=parse_mode,
    )


async def record_delivery_error(job, exc: BaseException, *, source: str) -> str:
    error_id = new_error_id()
    logger.exception(
        "Unexpected delivery failure error_id=%s job_id=%s bot_id=%s",
        error_id,
        job.id,
        job.bot_id,
        exc_info=exc,
    )
    await record_bot_error(
        error_id=error_id,
        source=source,
        exception=exc,
        telegram_chat_id=job.chat_id,
        extra={
            "bot_id": job.bot_id,
            "delivery_job_id": job.id,
            "delivery_kind": job.kind,
            "attempts": job.attempts,
        },
    )
    return error_id


async def deliver_job(
    bot: Bot,
    job,
    max_attempts: int,
) -> tuple[str, int | str, str | None]:
    try:
        message = await send_delivery(bot, job)
        return "delivered", message.message_id, None
    except TelegramRetryAfter as exc:
        return "retry", max(1, int(exc.retry_after)), str(exc)
    except (TelegramNetworkError, asyncio.TimeoutError) as exc:
        return "retry", retry_delay(job.attempts), str(exc)
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        return "failed", str(exc), str(exc)
    except Exception as exc:
        error_id = await record_delivery_error(job, exc, source="delivery_send")
        safe_error = f"Unexpected delivery error ({error_id})"
        if job.attempts + 1 >= max_attempts:
            return "failed", safe_error, safe_error
        return "retry", retry_delay(job.attempts), safe_error


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.json_logs)

    worker_id = os.getenv("DELIVERY_WORKER_ID") or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    interval = float(os.getenv("DELIVERY_POLL_INTERVAL_SECONDS", "1"))
    idle_max = float(os.getenv("DELIVERY_IDLE_MAX_SECONDS", str(settings.worker_idle_max_seconds)))
    idle_delay = interval
    batch_size = int(os.getenv("DELIVERY_BATCH_SIZE", "100"))
    max_attempts = int(os.getenv("DELIVERY_MAX_ATTEMPTS", "10"))
    stale_after = int(os.getenv("DELIVERY_LOCK_STALE_SECONDS", "120"))

    bot_pool = BotPool(settings)
    await init_database()
    mark_worker_heartbeat("delivery-worker", state="started", worker_id=worker_id)

    logger.info("Delivery worker started", extra={"worker_id": worker_id})

    try:
        while True:
            mark_worker_heartbeat("delivery-worker", state="polling", worker_id=worker_id)
            async with SessionFactory() as session:
                repository = DeliveryRepository(session)
                jobs = await repository.claim_batch(
                    worker_id=worker_id,
                    limit=batch_size,
                    stale_after_seconds=stale_after,
                )
                await session.commit()

            if not jobs:
                WORKER_BATCHES.labels("delivery", "empty").inc()
                WORKER_IDLE_SECONDS.labels("delivery").set(idle_delay)
                mark_worker_heartbeat(
                    "delivery-worker",
                    state="idle",
                    worker_id=worker_id,
                    idle_seconds=idle_delay,
                )
                await asyncio.sleep(idle_delay)
                idle_delay = next_idle_delay(idle_delay, interval, idle_max)
                continue

            WORKER_BATCHES.labels("delivery", "claimed").inc()
            WORKER_BATCH_SIZE.labels("delivery").observe(len(jobs))
            idle_delay = interval
            WORKER_IDLE_SECONDS.labels("delivery").set(idle_delay)
            mark_worker_heartbeat(
                "delivery-worker",
                state="processing",
                worker_id=worker_id,
                batch_size=len(jobs),
            )

            for claimed in jobs:
                async with SessionFactory() as session:
                    job = await session.get(type(claimed), claimed.id)
                    if job is None or job.status != "processing":
                        continue

                    instance = await session.get(BotInstance, job.bot_id)
                    if instance is None:
                        repository = DeliveryRepository(session)
                        await repository.mark_failed(job, error=f"Unknown bot instance: {job.bot_id}")
                        await session.commit()
                        continue

                    try:
                        bot = await bot_pool.for_instance(session, instance)
                    except RuntimeError as exc:
                        error_id = await record_delivery_error(job, exc, source="delivery_bot_credentials")
                        repository = DeliveryRepository(session)
                        await repository.mark_failed(
                            job,
                            error=f"Bot credentials unavailable ({error_id})",
                        )
                        await session.commit()
                        continue

                    status, value, error = await deliver_job(bot, job, max_attempts)

                    repository = DeliveryRepository(session)
                    if status == "delivered":
                        await repository.mark_delivered(job, telegram_message_id=int(value))
                    elif status == "retry" and job.attempts + 1 < max_attempts:
                        await repository.mark_retry(
                            job,
                            error=error or "Temporary Telegram delivery error",
                            delay_seconds=int(value),
                        )
                    else:
                        final_error = str(value)
                        await repository.mark_failed(job, error=final_error)
                        await mark_user_blocked_fallback(session, job, final_error)

                    await session.commit()
                    mark_worker_heartbeat(
                        "delivery-worker",
                        state="processing",
                        worker_id=worker_id,
                        last_job_id=job.id,
                        last_job_status=status,
                    )
    finally:
        await bot_pool.close()
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
