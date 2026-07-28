from __future__ import annotations

from collections.abc import Awaitable, Callable
import time
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.config import Settings
from app.core.performance import (
    observe_operation,
    reset_request_sql_stats,
    restore_request_sql_stats,
)


class PerformanceMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not self.settings.performance_enabled:
            return await handler(event, data)

        tokens = reset_request_sql_stats()
        started = time.perf_counter()
        status = "ok"
        try:
            return await handler(event, data)
        except Exception:
            status = "error"
            raise
        finally:
            observe_operation(
                component="telegram",
                operation=type(event).__name__,
                bot_code=self.settings.bot_code.strip().lower() or "unknown",
                status=status,
                started=started,
                slow_ms=self.settings.performance_slow_operation_ms,
                profile_enabled=self.settings.performance_profile_enabled,
            )
            restore_request_sql_stats(tokens)
