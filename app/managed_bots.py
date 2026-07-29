from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select

from app.bot.handlers import build_router
from app.bot.middlewares import DatabaseMiddleware, PerformanceMiddleware
from app.bot.middlewares.request_context import RequestContextMiddleware
from app.core.bot_context import CurrentBot
from app.core.config import load_settings
from app.core.logging import configure_logging
from app.database.session import SessionFactory, close_database, init_database
from app.models.bot_instance import BotInstance
from app.services.bot_credentials import resolve_bot_token

logger = logging.getLogger(__name__)


async def run_instance(instance: BotInstance, token: str, settings) -> None:
    bot = Bot(token=token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.outer_middleware(RequestContextMiddleware())
    dispatcher.update.outer_middleware(PerformanceMiddleware(settings))
    current = CurrentBot(instance.id, instance.code, instance.username, instance.display_name)
    middleware = DatabaseMiddleware(settings, current_bot=current)
    dispatcher.message.outer_middleware(middleware)
    dispatcher.callback_query.outer_middleware(middleware)
    dispatcher.include_router(build_router())
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.json_logs)
    await init_database()
    tasks: dict[int, asyncio.Task] = {}
    try:
        while True:
            async with SessionFactory() as session:
                instances = list((await session.execute(
                    select(BotInstance).where(
                        BotInstance.runtime_mode == "managed",
                        BotInstance.is_active.is_(True),
                        BotInstance.token_encrypted.is_not(None),
                    )
                )).scalars())
                active_ids = {item.id for item in instances}
                for bot_id, task in list(tasks.items()):
                    if bot_id not in active_ids or task.done():
                        task.cancel()
                        tasks.pop(bot_id, None)
                for item in instances:
                    if item.id not in tasks:
                        token = await resolve_bot_token(session, settings, item)
                        tasks[item.id] = asyncio.create_task(
                            run_instance(item, token, settings),
                            name=f"managed-bot-{item.code}",
                        )
                        logger.info("Managed project started", extra={"bot_code": item.code})
            await asyncio.sleep(20)
    finally:
        for task in tasks.values():
            task.cancel()
        await asyncio.gather(*tasks.values(), return_exceptions=True)
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
