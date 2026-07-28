from __future__ import annotations

import asyncio
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

from app.core.config import load_settings
from app.core.logging import configure_logging
from app.database.session import SessionFactory, close_database, init_database
from app.repositories.delivery import DeliveryRepository
from app.services.delivery import deserialize_markup

logger = logging.getLogger(__name__)


def retry_delay(attempt: int) -> int:
    return min(300, 2 ** min(attempt + 1, 8))



async def send_delivery(bot: Bot, job):
    markup = deserialize_markup(job.reply_markup)
    payload = job.payload or {}
    content_type = payload.get("content_type", "text")
    file_id = payload.get("file_id")
    caption = payload.get("caption") or job.text

    if content_type == "text" or not file_id:
        return await bot.send_message(
            chat_id=job.chat_id,
            text=job.text,
            reply_markup=markup,
        )

    common = {
        "chat_id": job.chat_id,
        "reply_markup": markup,
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
        return await bot.send_video_note(video_note=file_id, **common)
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
    )


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
        if job.attempts + 1 >= max_attempts:
            return "failed", str(exc), str(exc)
        return "retry", retry_delay(job.attempts), str(exc)


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.json_logs)

    worker_id = (
        os.getenv("DELIVERY_WORKER_ID")
        or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    )
    interval = float(os.getenv("DELIVERY_POLL_INTERVAL_SECONDS", "1"))
    batch_size = int(os.getenv("DELIVERY_BATCH_SIZE", "100"))
    max_attempts = int(os.getenv("DELIVERY_MAX_ATTEMPTS", "10"))
    stale_after = int(os.getenv("DELIVERY_LOCK_STALE_SECONDS", "120"))

    bot = Bot(token=settings.require_bot_token())
    await init_database()

    logger.info(
        "Delivery worker started",
        extra={"worker_id": worker_id},
    )

    try:
        while True:
            async with SessionFactory() as session:
                repository = DeliveryRepository(session)
                jobs = await repository.claim_batch(
                    worker_id=worker_id,
                    limit=batch_size,
                    stale_after_seconds=stale_after,
                )
                await session.commit()

            if not jobs:
                await asyncio.sleep(interval)
                continue

            for claimed in jobs:
                async with SessionFactory() as session:
                    job = await session.get(type(claimed), claimed.id)
                    if job is None or job.status != "processing":
                        continue

                    status, value, error = await deliver_job(
                        bot,
                        job,
                        max_attempts,
                    )

                    repository = DeliveryRepository(session)
                    if status == "delivered":
                        await repository.mark_delivered(
                            job,
                            telegram_message_id=int(value),
                        )
                    elif status == "retry" and job.attempts + 1 < max_attempts:
                        await repository.mark_retry(
                            job,
                            error=error or "Temporary Telegram delivery error",
                            delay_seconds=int(value),
                        )
                    else:
                        await repository.mark_failed(
                            job,
                            error=str(value),
                        )

                    await session.commit()
    finally:
        await bot.session.close()
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
