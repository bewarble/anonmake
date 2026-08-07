from __future__ import annotations

import json
import logging
import secrets
from typing import Any

from app.core.bot_context import get_current_bot
from app.database.session import SessionFactory
from app.models.admin import AdminAuditLog

logger = logging.getLogger(__name__)


def new_error_id() -> str:
    return f"err_{secrets.token_hex(6)}"


def safe_exception_type(exc: BaseException | None) -> str | None:
    if exc is None:
        return None
    return type(exc).__name__[:120]


def decode_bot_error_event(row: AdminAuditLog) -> dict[str, Any]:
    try:
        details = json.loads(row.details or "{}")
    except (TypeError, json.JSONDecodeError):
        details = {}
    return {
        "error_id": row.target or "—",
        "created_at": row.created_at,
        "source": details.get("source") or "—",
        "exception_type": details.get("exception_type") or "—",
        "telegram_user_id": details.get("telegram_user_id"),
        "telegram_chat_id": details.get("telegram_chat_id"),
        "update_id": details.get("update_id"),
        "update_type": details.get("update_type") or "—",
        "request_id": details.get("request_id") or "—",
        "bot_id": details.get("bot_id"),
        "bot_code": details.get("bot_code") or "—",
        "bot_username": details.get("bot_username") or "—",
    }


async def record_bot_error(
    *,
    error_id: str,
    source: str,
    exception: BaseException | None = None,
    telegram_user_id: int | None = None,
    telegram_chat_id: int | None = None,
    update_id: int | None = None,
    update_type: str | None = None,
    request_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    bot = get_current_bot()
    details: dict[str, Any] = {
        "source": source[:160],
        "exception_type": safe_exception_type(exception),
        "telegram_user_id": telegram_user_id,
        "telegram_chat_id": telegram_chat_id,
        "update_id": update_id,
        "update_type": (update_type or "unknown")[:80],
        "request_id": request_id[:128] if request_id else None,
        "bot_id": bot.id if bot else None,
        "bot_code": bot.code if bot else None,
        "bot_username": bot.username if bot else None,
    }
    if extra:
        for key, value in extra.items():
            if key in {"traceback", "token", "secret", "exception", "password"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                details[str(key)[:80]] = value if not isinstance(value, str) else value[:500]

    try:
        async with SessionFactory() as session:
            session.add(
                AdminAuditLog(
                    admin_telegram_id=0,
                    action="bot_error",
                    target=error_id,
                    details=json.dumps(details, ensure_ascii=False, separators=(",", ":")),
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Could not persist bot error event error_id=%s", error_id)
