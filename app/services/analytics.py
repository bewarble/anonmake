from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Question, User
from app.models.billing import PaymentAttempt, Subscription
from app.models.reveal import RevealCheckout


@dataclass(slots=True, frozen=True)
class AnalyticsSnapshot:
    users_total: int
    users_1d: int
    users_7d: int
    users_30d: int

    questions_total: int
    questions_1d: int
    questions_7d: int
    questions_30d: int

    answers_total: int
    answers_1d: int
    answers_7d: int
    answers_30d: int

    reveals_total: int
    active_vip: int

    payments_success: int
    payments_failed: int
    revenue_kopecks: int

    @property
    def answer_rate(self) -> float:
        if self.questions_total == 0:
            return 0.0
        return self.answers_total / self.questions_total * 100

    @property
    def reveal_rate(self) -> float:
        if self.questions_total == 0:
            return 0.0
        return self.reveals_total / self.questions_total * 100

    @property
    def vip_rate(self) -> float:
        if self.users_total == 0:
            return 0.0
        return self.active_vip / self.users_total * 100


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def snapshot(self) -> AnalyticsSnapshot:
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        return AnalyticsSnapshot(
            users_total=await self._count(User),
            users_1d=await self._count_since(User, day_ago),
            users_7d=await self._count_since(User, week_ago),
            users_30d=await self._count_since(User, month_ago),
            questions_total=await self._count(Question),
            questions_1d=await self._count_since(Question, day_ago),
            questions_7d=await self._count_since(Question, week_ago),
            questions_30d=await self._count_since(Question, month_ago),
            answers_total=await self._count(Answer),
            answers_1d=await self._count_since(Answer, day_ago),
            answers_7d=await self._count_since(Answer, week_ago),
            answers_30d=await self._count_since(Answer, month_ago),
            reveals_total=await self._count_successful_reveals(),
            active_vip=await self._count_active_vip(now),
            payments_success=await self._count_successful_payments(),
            payments_failed=await self._count_failed_payments(),
            revenue_kopecks=await self._sum_revenue(),
        )

    async def _count(self, model) -> int:
        value = await self.session.scalar(select(func.count(model.id)))
        return int(value or 0)

    async def _count_since(self, model, since: datetime) -> int:
        value = await self.session.scalar(
            select(func.count(model.id)).where(model.created_at >= since)
        )
        return int(value or 0)

    async def _count_successful_reveals(self) -> int:
        value = await self.session.scalar(
            select(func.count(RevealCheckout.id)).where(
                RevealCheckout.status.in_(("paid", "completed", "success"))
            )
        )
        return int(value or 0)

    async def _count_active_vip(self, now: datetime) -> int:
        value = await self.session.scalar(
            select(func.count(Subscription.id)).where(
                Subscription.access_until.is_not(None),
                Subscription.access_until > now,
            )
        )
        return int(value or 0)

    async def _count_successful_payments(self) -> int:
        value = await self.session.scalar(
            select(func.count(PaymentAttempt.id)).where(
                PaymentAttempt.status.in_(("success", "paid", "completed"))
            )
        )
        return int(value or 0)

    async def _count_failed_payments(self) -> int:
        value = await self.session.scalar(
            select(func.count(PaymentAttempt.id)).where(
                PaymentAttempt.status.in_(("failed", "declined", "error"))
            )
        )
        return int(value or 0)

    async def _sum_revenue(self) -> int:
        value = await self.session.scalar(
            select(
                func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)
            ).where(
                PaymentAttempt.status.in_(("success", "paid", "completed"))
            )
        )
        return int(value or 0)
