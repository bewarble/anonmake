from __future__ import annotations

from dataclasses import dataclass
import hashlib

from redis.asyncio import Redis


@dataclass(slots=True)
class GuardDecision:
    allowed: bool
    reason: str | None = None


class AbuseGuard:
    """Sender-scoped protection. Recipients are never globally rate-limited."""

    def __init__(
        self,
        redis: Redis,
        burst_limit: int = 4,
        burst_window_seconds: int = 8,
        minute_limit: int = 20,
        duplicate_window_seconds: int = 180,
    ) -> None:
        self.redis = redis
        self.burst_limit = burst_limit
        self.burst_window_seconds = burst_window_seconds
        self.minute_limit = minute_limit
        self.duplicate_window_seconds = duplicate_window_seconds

    async def check_question(
        self,
        sender_telegram_id: int,
        recipient_user_id: int,
        text: str,
    ) -> GuardDecision:
        sender = str(sender_telegram_id)

        if not await self._window(
            f"abuse:burst:{sender}",
            self.burst_limit,
            self.burst_window_seconds,
        ):
            return GuardDecision(False, "too_fast")

        if not await self._window(
            f"abuse:minute:{sender}",
            self.minute_limit,
            60,
        ):
            return GuardDecision(False, "too_fast")

        normalized = " ".join(text.casefold().split())
        digest = hashlib.sha256(
            f"{sender}:{recipient_user_id}:{normalized}".encode()
        ).hexdigest()

        created = await self.redis.set(
            f"abuse:duplicate:{digest}",
            "1",
            ex=self.duplicate_window_seconds,
            nx=True,
        )
        if not created:
            return GuardDecision(False, "duplicate")

        return GuardDecision(True)

    async def _window(self, key: str, limit: int, ttl: int) -> bool:
        value = await self.redis.incr(key)
        if value == 1:
            await self.redis.expire(key, ttl)
        return value <= limit
