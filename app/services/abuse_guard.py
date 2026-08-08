from __future__ import annotations

from dataclasses import dataclass
import hashlib

from redis.asyncio import Redis

from app.core.bot_context import require_current_bot


@dataclass(slots=True, frozen=True)
class GuardDecision:
    allowed: bool
    reason: str | None = None


class AbuseGuard:
    """Distributed protection scoped to one sender inside one Telegram project.

    A popular recipient is never globally rate-limited. Ten thousand distinct
    users may write to the same blogger at the same time; only abusive behavior
    from an individual sender in the current bot is slowed down.
    """

    def __init__(
        self,
        redis: Redis,
        *,
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

    @staticmethod
    def _namespace(sender_telegram_id: int) -> str:
        bot_id = require_current_bot().id
        return f"{bot_id}:{sender_telegram_id}"

    async def check_question(
        self,
        *,
        sender_telegram_id: int,
        recipient_user_id: int,
        text: str,
    ) -> GuardDecision:
        sender = self._namespace(sender_telegram_id)

        if not await self._window(
            f"abuse:question:burst:{sender}",
            self.burst_limit,
            self.burst_window_seconds,
        ):
            return GuardDecision(False, "too_fast")

        if not await self._window(
            f"abuse:question:minute:{sender}",
            self.minute_limit,
            60,
        ):
            return GuardDecision(False, "too_fast")

        normalized = " ".join(text.casefold().split())
        digest = hashlib.sha256(
            f"{sender}:{recipient_user_id}:{normalized}".encode("utf-8")
        ).hexdigest()

        accepted = await self.redis.set(
            f"abuse:question:duplicate:{digest}",
            "1",
            ex=self.duplicate_window_seconds,
            nx=True,
        )
        if not accepted:
            return GuardDecision(False, "duplicate")

        return GuardDecision(True)

    async def rollback_duplicate(
        self,
        *,
        sender_telegram_id: int,
        recipient_user_id: int,
        text: str,
    ) -> None:
        """Allow retry when database persistence or delivery failed."""

        sender = self._namespace(sender_telegram_id)
        normalized = " ".join(text.casefold().split())
        digest = hashlib.sha256(
            f"{sender}:{recipient_user_id}:{normalized}".encode("utf-8")
        ).hexdigest()
        await self.redis.delete(f"abuse:question:duplicate:{digest}")

    async def _window(self, key: str, limit: int, ttl: int) -> bool:
        # INCR and the first EXPIRE must be atomic; otherwise a process crash
        # between the two commands can leave a permanent rate-limit key.
        value = await self.redis.eval(
            """
            local current = redis.call('INCR', KEYS[1])
            if current == 1 then
                redis.call('EXPIRE', KEYS[1], ARGV[1])
            end
            return current
            """,
            1,
            key,
            ttl,
        )
        return int(value) <= limit
