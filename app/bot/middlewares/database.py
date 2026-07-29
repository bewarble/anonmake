from __future__ import annotations

from collections.abc import Awaitable, Callable
import asyncio
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.bot_context import CurrentBot, reset_current_bot, set_current_bot
from app.core.config import Settings
from app.database.session import SessionFactory
from app.repositories.bot_instances import BotInstanceRepository


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings, current_bot: CurrentBot | None = None) -> None:
        self.settings = settings
        self._current_bot: CurrentBot | None = current_bot
        self._bootstrap_lock = asyncio.Lock()

    async def _resolve_current_bot(self) -> CurrentBot:
        if self._current_bot is not None:
            return self._current_bot

        async with self._bootstrap_lock:
            if self._current_bot is not None:
                return self._current_bot

            code, username, display_name = self.settings.require_bot_identity()
            async with SessionFactory() as session:
                instance = await BotInstanceRepository(session).get_or_create(
                    code=code,
                    username=username,
                    display_name=display_name,
                )
                await session.commit()
                self._current_bot = CurrentBot(
                    id=instance.id,
                    code=instance.code,
                    username=instance.username,
                    display_name=instance.display_name,
                )
            return self._current_bot

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        current_bot = await self._resolve_current_bot()

        async with SessionFactory() as session:
            token = set_current_bot(current_bot)
            data["session"] = session
            data["bot_instance"] = current_bot

            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
            finally:
                reset_current_bot(token)
