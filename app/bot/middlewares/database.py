from __future__ import annotations

from collections.abc import Awaitable, Callable
import asyncio
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.bot_context import CurrentBot, reset_current_bot, set_current_bot
from app.core.config import Settings
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.repositories.bot_instances import BotInstanceRepository


DEFAULT_MAINTENANCE_MESSAGE = "⚙️ Бот временно находится на техническом обслуживании. Попробуйте позже."
DEFAULT_INACTIVE_MESSAGE = "⚙️ Бот временно недоступен. Попробуйте позже."


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

    @staticmethod
    def _event_user_id(event: TelegramObject) -> int | None:
        if isinstance(event, (Message, CallbackQuery)) and event.from_user is not None:
            return event.from_user.id
        return None

    async def _deny_user_event(self, event: TelegramObject, text: str) -> None:
        if isinstance(event, CallbackQuery):
            # Always stop Telegram's callback spinner even if the source message
            # has already disappeared or cannot be edited/replied to.
            await event.answer(text[:200], show_alert=True)
            return
        if isinstance(event, Message):
            await event.answer(text)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        cached_bot = await self._resolve_current_bot()

        async with SessionFactory() as session:
            # Runtime switches in the web admin must take effect immediately.
            # Do not trust the BotInstance snapshot captured when polling began.
            instance = await session.get(BotInstance, cached_bot.id)
            if instance is None:
                return None

            current_bot = CurrentBot(
                id=instance.id,
                code=instance.code,
                username=instance.username,
                display_name=instance.display_name,
            )
            self._current_bot = current_bot

            token = set_current_bot(current_bot)
            data["session"] = session
            data["bot_instance"] = current_bot

            try:
                user_id = self._event_user_id(event)
                is_user_event = isinstance(event, (Message, CallbackQuery))
                is_telegram_admin = user_id in self.settings.admin_ids_set if user_id is not None else False

                if is_user_event and not instance.is_active:
                    await self._deny_user_event(event, DEFAULT_INACTIVE_MESSAGE)
                    await session.commit()
                    return None

                if is_user_event and instance.is_maintenance and not is_telegram_admin:
                    message = (instance.maintenance_message or "").strip() or DEFAULT_MAINTENANCE_MESSAGE
                    await self._deny_user_event(event, message)
                    await session.commit()
                    return None

                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
            finally:
                reset_current_bot(token)
