from __future__ import annotations

import asyncio
import hashlib
import logging
import time

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

RECONCILE_SECONDS = 20
MAX_RESTART_BACKOFF_SECONDS = 600
STABLE_RUNTIME_SECONDS = 300


def token_fingerprint(token: str) -> str:
    """Compare credentials without keeping or logging the token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def credential_revision(instance: BotInstance) -> str:
    """Detect operator edits without exposing encrypted credentials."""
    verified = instance.token_verified_at.isoformat() if instance.token_verified_at else ""
    updated = instance.updated_at.isoformat() if instance.updated_at else ""
    return f"{instance.token_hint or ''}|{verified}|{updated}"


def restart_backoff_seconds(failure_count: int) -> int:
    exponent = max(0, min(failure_count - 1, 10))
    return min(RECONCILE_SECONDS * (2**exponent), MAX_RESTART_BACKOFF_SECONDS)


async def run_instance(instance: BotInstance, token: str, settings) -> None:
    stage = "init"
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
        stage = "delete_webhook"
        await bot.delete_webhook(drop_pending_updates=False)
        stage = "set_commands"
        await sync_public_commands(bot)
        stage = "polling"
        logger.info("Managed project entering polling", extra={"bot_code": instance.code})
        await dispatcher.start_polling(bot)
    except Exception as exc:
        setattr(exc, "managed_runtime_stage", stage)
        raise
    finally:
        await storage.close()
        await bot.session.close()


async def record_runtime_crash(instance: BotInstance, exc: BaseException) -> None:
    error_id = new_error_id()
    stage = getattr(exc, "managed_runtime_stage", "unknown")
    safe_error = str(exc).replace("\n", " ")[:500]
    logger.error(
        "Managed bot runtime stopped unexpectedly error_id=%s bot_code=%s stage=%s exception_type=%s error=%s",
        error_id,
        instance.code,
        stage,
        type(exc).__name__,
        safe_error,
    )
    await record_bot_error(
        error_id=error_id,
        source="managed_bot_runtime",
        exception=exc,
        extra={
            "bot_id": instance.id,
            "bot_code": instance.code,
            "bot_username": instance.username,
            "runtime_stage": stage,
            "error_message": safe_error,
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
    running_fingerprints: dict[int, str] = {}
    last_resolved_fingerprints: dict[int, str] = {}
    last_credential_revisions: dict[int, str] = {}
    task_started_at: dict[int, float] = {}
    failure_counts: dict[int, int] = {}
    retry_after: dict[int, float] = {}
    known_instances: dict[int, BotInstance] = {}
    mark_worker_heartbeat("managed-bots", state="started", active_count=0)
    try:
        while True:
            now_monotonic = time.monotonic()
            async with SessionFactory() as session:
                instances = list((await session.execute(
                    select(BotInstance).where(
                        BotInstance.runtime_mode == "managed",
                        BotInstance.is_active.is_(True),
                    )
                )).scalars())
                known_instances.update({item.id: item for item in instances})
                active_ids = {item.id for item in instances}
                crash_count = 0

                for bot_id, task in list(tasks.items()):
                    started_at = task_started_at.get(bot_id, now_monotonic)
                    if not task.done() and now_monotonic - started_at >= STABLE_RUNTIME_SECONDS:
                        failure_counts.pop(bot_id, None)
                        retry_after.pop(bot_id, None)

                    if task.done():
                        instance = known_instances.get(bot_id)
                        if not task.cancelled():
                            exc = task.exception()
                            if exc is None:
                                exc = RuntimeError("Managed polling stopped unexpectedly")
                                setattr(exc, "managed_runtime_stage", "polling")
                            if instance is not None:
                                crash_count += 1
                                await record_runtime_crash(instance, exc)
                            failures = failure_counts.get(bot_id, 0) + 1
                            failure_counts[bot_id] = failures
                            delay = restart_backoff_seconds(failures)
                            retry_after[bot_id] = now_monotonic + delay
                            logger.warning(
                                "Managed project restart backed off bot_id=%s failures=%s delay_seconds=%s",
                                bot_id,
                                failures,
                                delay,
                            )
                        tasks.pop(bot_id, None)
                        running_fingerprints.pop(bot_id, None)
                        task_started_at.pop(bot_id, None)
                        continue

                    if bot_id not in active_ids:
                        await stop_task(task)
                        tasks.pop(bot_id, None)
                        running_fingerprints.pop(bot_id, None)
                        task_started_at.pop(bot_id, None)
                        failure_counts.pop(bot_id, None)
                        retry_after.pop(bot_id, None)
                        last_resolved_fingerprints.pop(bot_id, None)
                        last_credential_revisions.pop(bot_id, None)

                for bot_id in set(failure_counts) - active_ids:
                    failure_counts.pop(bot_id, None)
                    retry_after.pop(bot_id, None)
                    last_resolved_fingerprints.pop(bot_id, None)
                    last_credential_revisions.pop(bot_id, None)

                for item in instances:
                    revision = credential_revision(item)
                    previous_revision = last_credential_revisions.get(item.id)
                    if previous_revision is not None and previous_revision != revision:
                        failure_counts.pop(item.id, None)
                        retry_after.pop(item.id, None)
                    last_credential_revisions[item.id] = revision

                    try:
                        token = await resolve_bot_token(session, settings, item)
                    except Exception as exc:
                        if now_monotonic < retry_after.get(item.id, 0.0):
                            continue
                        crash_count += 1
                        await record_runtime_crash(item, exc)
                        failures = failure_counts.get(item.id, 0) + 1
                        failure_counts[item.id] = failures
                        retry_after[item.id] = now_monotonic + restart_backoff_seconds(failures)
                        continue

                    fingerprint = token_fingerprint(token)
                    previous_resolved = last_resolved_fingerprints.get(item.id)
                    if previous_resolved is not None and previous_resolved != fingerprint:
                        # A repaired/rotated credential must override a stale
                        # crash backoff, even when no task is currently alive.
                        failure_counts.pop(item.id, None)
                        retry_after.pop(item.id, None)
                    last_resolved_fingerprints[item.id] = fingerprint

                    running_task = tasks.get(item.id)
                    running_fingerprint = running_fingerprints.get(item.id)
                    if running_task is not None and running_fingerprint != fingerprint:
                        logger.info(
                            "Managed project credential changed; restarting",
                            extra={"bot_code": item.code},
                        )
                        await stop_task(running_task)
                        tasks.pop(item.id, None)
                        running_fingerprints.pop(item.id, None)
                        task_started_at.pop(item.id, None)
                        failure_counts.pop(item.id, None)
                        retry_after.pop(item.id, None)

                    if item.id not in tasks:
                        if now_monotonic < retry_after.get(item.id, 0.0):
                            continue
                        tasks[item.id] = asyncio.create_task(
                            run_instance(item, token, settings),
                            name=f"managed-bot-{item.code}",
                        )
                        running_fingerprints[item.id] = fingerprint
                        task_started_at[item.id] = now_monotonic
                        logger.info("Managed project started", extra={"bot_code": item.code})

                backoff_count = sum(
                    1
                    for bot_id in active_ids
                    if now_monotonic < retry_after.get(bot_id, 0.0)
                )
                mark_worker_heartbeat(
                    "managed-bots",
                    state="polling",
                    configured_count=len(instances),
                    active_count=len(tasks),
                    backoff_count=backoff_count,
                    crash_count=crash_count,
                )
            await asyncio.sleep(RECONCILE_SECONDS)
    finally:
        mark_worker_heartbeat("managed-bots", state="stopping", active_count=len(tasks))
        for task in tasks.values():
            task.cancel()
        await asyncio.gather(*tasks.values(), return_exceptions=True)
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
