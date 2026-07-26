from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
import uuid

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.logging import request_id_var


class RequestContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        request_id = uuid.uuid4().hex
        token = request_id_var.set(request_id)
        try:
            data["request_id"] = request_id
            return await handler(event, data)
        finally:
            request_id_var.reset(token)
