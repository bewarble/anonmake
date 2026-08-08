from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from sqlalchemy import select

from app.bot.commands import sync_public_commands
from app.bot.handlers import build_router
from app.bot.middlewares import DatabaseMiddleware, PerformanceMiddleware
from app.bot.middlewares.request_context import RequestContextMiddleware
from app.bot.storage import build_fsm_storage
from app.core.config import load_settings
from app.core.logging import configure_logging
from app.database.session import SessionFactory, close_database, init_database
from app.models.bot_instance import BotInstance
from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)


async def _project_is_managed(bot_code: str) -> bool:
    async with SessionFactory() as session:
        instance = await session.scalar(
            select(BotInstance).where(BotInstance.code == bot_code)
        )
        return bool(
            instance is not None
            and instance.runtime_mode == "managed"
            and instance.is_active
            and instance.token_encrypted
        )


async def _stand_by_for_managed_runtime(bot_code: str) -> None:
    logger.info(
        "Legacy bot runtime disabled because project is managed",
        extra={"bot_code": bot_code},
    )
    while True:
        await asyncio.sleep(3600)


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.json_logs)

    await init_database()
    try:
        if await _project_is_managed(settings.bot_code):
            await _stand_by_for_managed_runtime(settings.bot_code)
            return

        bot = Bot(token=settings.require_bot_token())
        storage = build_fsm_storage(settings.redis_url)
        dispatcher = Dispatcher(storage=storage)
        dispatcher.update.outer_middleware(RequestContextMiddleware())
        dispatcher.update.outer_middleware(PerformanceMiddleware(settings))

        database_middleware = DatabaseMiddleware(settings)
        dispatcher.message.outer_middleware(database_middleware)
        dispatcher.callback_query.outer_middleware(database_middleware)
        dispatcher.my_chat_member.outer_middleware(database_middleware)
        dispatcher.include_router(build_router())

        try:
            await bot.delete_webhook(drop_pending_updates=False)
            await sync_public_commands(bot)
            await dispatcher.start_polling(bot)
        finally:
            await storage.close()
            await get_redis(settings.redis_url).aclose()
            await bot.session.close()
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
