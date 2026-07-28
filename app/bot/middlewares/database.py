from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.bot_context import CurrentBot, reset_current_bot, set_current_bot
from app.core.config import Settings
from app.database.session import SessionFactory
from app.repositories.bot_instances import BotInstanceRepository


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        code, username, display_name = self.settings.require_bot_identity()

        async with SessionFactory() as session:
            instance = await BotInstanceRepository(session).get_or_create(
                code=code,
                username=username,
                display_name=display_name,
            )
            await session.commit()

            token = set_current_bot(
                CurrentBot(
                    id=instance.id,
                    code=instance.code,
                    username=instance.username,
                    display_name=instance.display_name,
                )
            )
            data["session"] = session
            data["bot_instance"] = instance

            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
            finally:
                reset_current_bot(token)
