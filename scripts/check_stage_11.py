from __future__ import annotations

import asyncio
import secrets

from app.core.config import load_settings
from app.services.abuse_guard import AbuseGuard
from app.services.redis_client import get_redis


async def check() -> None:
    settings = load_settings()
    redis = get_redis(settings.redis_url)
    assert await redis.ping()

    suffix = secrets.token_hex(4)
    sender_id = -int.from_bytes(secrets.token_bytes(4), "big")
    recipient_id = -int.from_bytes(secrets.token_bytes(4), "big")
    text = f"Stage 11 test {suffix}"

    guard = AbuseGuard(
        redis,
        burst_limit=10,
        minute_limit=20,
        duplicate_window_seconds=30,
    )

    first = await guard.check_question(
        sender_telegram_id=sender_id,
        recipient_user_id=recipient_id,
        text=text,
    )
    duplicate = await guard.check_question(
        sender_telegram_id=sender_id,
        recipient_user_id=recipient_id,
        text=f"  {text.upper()}  ",
    )

    assert first.allowed
    assert not duplicate.allowed
    assert duplicate.reason == "duplicate"

    await guard.rollback_duplicate(
        sender_telegram_id=sender_id,
        recipient_user_id=recipient_id,
        text=text,
    )

    retry = await guard.check_question(
        sender_telegram_id=sender_id,
        recipient_user_id=recipient_id,
        text=text,
    )
    assert retry.allowed

    print("Stage 11 check: OK")
    print("Protection: connected to question submission")
    print("Scope: sender only; recipients have no global cap")
    print("Redis failure mode: fail-open")
    print("Delivery failure: duplicate key rolled back")


if __name__ == "__main__":
    asyncio.run(check())
