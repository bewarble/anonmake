from redis.asyncio import Redis


class IdempotencyGuard:
    def __init__(self, redis: Redis, namespace: str = "idempotency") -> None:
        self.redis = redis
        self.namespace = namespace

    async def acquire(self, key: str, ttl_seconds: int = 3600) -> bool:
        result = await self.redis.set(
            f"{self.namespace}:{key}",
            "1",
            ex=ttl_seconds,
            nx=True,
        )
        return bool(result)

    async def release(self, key: str) -> None:
        await self.redis.delete(f"{self.namespace}:{key}")
