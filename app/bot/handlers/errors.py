from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from app.core import texts

router = Router(name="errors")
logger = logging.getLogger(__name__)


@router.errors()
async def handle_error(event: ErrorEvent) -> bool:
    logger.exception(
        "Unhandled Telegram update error",
        exc_info=event.exception,
    )

    update = event.update

    message = getattr(update, "message", None)
    if message is not None:
        try:
            await message.answer(texts.TEMPORARY_ERROR)
        except Exception:
            logger.exception("Could not send fallback error message")
        return True

    callback = getattr(update, "callback_query", None)
    if callback is not None:
        try:
            await callback.answer(
                texts.TEMPORARY_ERROR,
                show_alert=True,
            )
        except Exception:
            logger.exception("Could not answer failed callback")
        return True

    return True
