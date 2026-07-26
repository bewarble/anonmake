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


async def deliver_job(bot: Bot, job, max_attempts: int) -> tuple[str, int | str]:
    try:
        message = await bot.send_message(
            chat_id=job.chat_id,
            text=job.text,
            reply_markup=deserialize_markup(job.reply_markup),
        )
        return "delivered", message.message_id
    except TelegramRetryAfter as exc:
        return "retry", max(1, int(exc.retry_after))
    except (TelegramNetworkError, asyncio.TimeoutError) as exc:
        return "retry", retry_delay(job.attempts)
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        return "failed", str(exc)
    except Exception as exc:
        if job.attempts + 1 >= max_attempts:
            return "failed", str(exc)
        return "retry", retry_delay(job.attempts)


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

                    status, value = await deliver_job(
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
                            error="Temporary Telegram delivery error",
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
