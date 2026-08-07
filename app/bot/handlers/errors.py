from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from app.core import texts
from app.core.error_diagnostics import new_error_id, record_bot_error

router = Router(name="errors")
logger = logging.getLogger(__name__)


@router.errors()
async def handle_error(event: ErrorEvent, request_id: str | None = None) -> bool:
    error_id = new_error_id()
    update = event.update
    message = getattr(update, "message", None)
    callback = getattr(update, "callback_query", None)

    telegram_user_id = None
    telegram_chat_id = None
    if message is not None:
        telegram_user_id = getattr(getattr(message, "from_user", None), "id", None)
        telegram_chat_id = getattr(getattr(message, "chat", None), "id", None)
    elif callback is not None:
        telegram_user_id = getattr(getattr(callback, "from_user", None), "id", None)
        callback_message = getattr(callback, "message", None)
        telegram_chat_id = getattr(getattr(callback_message, "chat", None), "id", None)

    try:
        update_type = update.event_type
    except Exception:
        update_type = "unknown"

    logger.exception(
        "Unhandled Telegram update error error_id=%s update_id=%s update_type=%s",
        error_id,
        getattr(update, "update_id", None),
        update_type,
        exc_info=event.exception,
    )
    await record_bot_error(
        error_id=error_id,
        source="telegram_update",
        exception=event.exception,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_chat_id,
        update_id=getattr(update, "update_id", None),
        update_type=update_type,
        request_id=request_id,
    )

    user_text = texts.TEMPORARY_ERROR_WITH_ID.format(error_id=error_id)
    if message is not None:
        try:
            await message.answer(user_text)
        except Exception:
            logger.exception("Could not send Telegram error message error_id=%s", error_id)
        return True

    if callback is not None:
        try:
            await callback.answer(user_text, show_alert=True)
        except Exception:
            logger.exception("Could not answer failed callback error_id=%s", error_id)
        return True

    return True
