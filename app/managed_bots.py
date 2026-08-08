from __future__ import annotations

import asyncio
import hashlib
import logging

from aiogram import Bot, Dispatcher
from sqlalchemy import select

from app.bot.commands import sync_public_commands
from app.bot.handlers import build_router
from app.bot.middlewares import DatabaseMiddleware, PerformanceMiddleware
from app.bot.middlewares.request_context import RequestContextMiddleware
from app.bot.storage import build_fsm_storage
from app.core.bot_context import CurrentBot
from app.core.config import load_settings
from app.core.error_diagnostics import new_error_id, record_bot_error
from app.core.logging import configure_logging
from app.core.worker_health import mark_worker_heartbeat
from app.database.session import SessionFactory, close_database, init_database
from app.models.bot_instance import BotInstance
from app.services.bot_credentials import resolve_bot_token

logger = logging.getLogger(__name__)


def token_fingerprint(token: str) -> str:
    """Compare credentials without keeping or logging the token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def run_instance(instance: BotInstance, token: str, settings) -> None:
    bot = Bot(token=token)
    storage = build_fsm_storage(settings.redis_url)
    dispatcher = Dispatcher(storage=storage)
    dispatcher.update.outer_middleware(RequestContextMiddleware())
    dispatcher.update.outer_middleware(PerformanceMiddleware(settings))
    current = CurrentBot(instance.id, instance.code, instance.username, instance.display_name)
    middleware = DatabaseMiddleware(settings, current_bot=current)
    dispatcher.message.outer_middleware(middleware)
    dispatcher.callback_query.outer_middleware(middleware)
    dispatcher.my_chat_member.outer_middleware(middleware)
    dispatcher.include_router(build_router())
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await sync_public_commands(bot)
        await dispatcher.start_polling(bot)
    finally:
        await storage.close()
        await bot.session.close()


async def record_runtime_crash(instance: BotInstance, exc: BaseException) -> None:
    error_id = new_error_id()
    logger.error(
        "Managed bot runtime stopped unexpectedly error_id=%s bot_code=%s exception_type=%s",
        error_id,
        instance.code,
        type(exc).__name__,
    )
    await record_bot_error(
        error_id=error_id,
        source="managed_bot_runtime",
        exception=exc,
        extra={
            "bot_id": instance.id,
            "bot_code": instance.code,
            "bot_username": instance.username,
        },
    )


async def stop_task(task: asyncio.Task) -> None:
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.json_logs)
    await init_database()
    tasks: dict[int, asyncio.Task] = {}
    task_token_fingerprints: dict[int, str] = {}
    known_instances: dict[int, BotInstance] = {}
    mark_worker_heartbeat("managed-bots", state="started", active_count=0)
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
                known_instances.update({item.id: item for item in instances})
                active_ids = {item.id for item in instances}
                crash_count = 0
                for bot_id, task in list(tasks.items()):
                    if task.done():
                        if not task.cancelled():
                            exc = task.exception()
                            instance = known_instances.get(bot_id)
                            if exc is not None and instance is not None:
                                crash_count += 1
                                await record_runtime_crash(instance, exc)
                        tasks.pop(bot_id, None)
                        task_token_fingerprints.pop(bot_id, None)
                        continue
                    if bot_id not in active_ids:
                        await stop_task(task)
                        tasks.pop(bot_id, None)
                        task_token_fingerprints.pop(bot_id, None)

                for item in instances:
                    token = await resolve_bot_token(session, settings, item)
                    fingerprint = token_fingerprint(token)
                    running_task = tasks.get(item.id)
                    if (
                        running_task is not None
                        and task_token_fingerprints.get(item.id) != fingerprint
                    ):
                        logger.info(
                            "Managed project credential changed; restarting",
                            extra={"bot_code": item.code},
                        )
                        await stop_task(running_task)
                        tasks.pop(item.id, None)
                        task_token_fingerprints.pop(item.id, None)

                    if item.id not in tasks:
                        tasks[item.id] = asyncio.create_task(
                            run_instance(item, token, settings),
                            name=f"managed-bot-{item.code}",
                        )
                        task_token_fingerprints[item.id] = fingerprint
                        logger.info("Managed project started", extra={"bot_code": item.code})
                mark_worker_heartbeat(
                    "managed-bots",
                    state="polling",
                    configured_count=len(instances),
                    active_count=len(tasks),
                    crash_count=crash_count,
                )
            await asyncio.sleep(20)
    finally:
        mark_worker_heartbeat("managed-bots", state="stopping", active_count=len(tasks))
        for task in tasks.values():
            task.cancel()
        await asyncio.gather(*tasks.values(), return_exceptions=True)
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
