from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import build_router
from app.bot.middlewares import DatabaseMiddleware
from app.bot.middlewares.request_context import RequestContextMiddleware
from app.core.config import load_settings
from app.core.logging import configure_logging
from app.database.session import close_database, init_database
from app.services.redis_client import get_redis


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.json_logs)

    bot = Bot(token=settings.require_bot_token())
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.outer_middleware(RequestContextMiddleware())

    database_middleware = DatabaseMiddleware()
    dispatcher.message.outer_middleware(database_middleware)
    dispatcher.callback_query.outer_middleware(database_middleware)
    dispatcher.include_router(build_router())

    await init_database()
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot)
    finally:
        await get_redis(settings.redis_url).aclose()
        await close_database()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
