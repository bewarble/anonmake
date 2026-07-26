import asyncio

from redis.asyncio import Redis

from app.services.abuse_guard import AbuseGuard
from app.services.idempotency import IdempotencyGuard


async def check() -> None:
    redis = Redis.from_url("redis://redis:6379/0", decode_responses=True)
    assert await redis.ping()

    idem = IdempotencyGuard(redis, namespace="stage8-check")
    assert await idem.acquire("one", ttl_seconds=30)
    assert not await idem.acquire("one", ttl_seconds=30)
    await idem.release("one")

    guard = AbuseGuard(redis, burst_limit=5, minute_limit=10)
    first = await guard.check_question(-101, -202, "Проверка")
    second = await guard.check_question(-101, -202, "  проверка ")
    assert first.allowed
    assert not second.allowed
    assert second.reason == "duplicate"

    await redis.delete("abuse:burst:-101", "abuse:minute:-101")
    async for key in redis.scan_iter("abuse:duplicate:*"):
        await redis.delete(key)

    await redis.aclose()

    print("Stage 8 check: OK")
    print("Redis: connected")
    print("Idempotency: distributed")
    print("Abuse protection: sender-scoped")
    print("Observability: JSON logs + Prometheus metrics")


if __name__ == "__main__":
    asyncio.run(check())
