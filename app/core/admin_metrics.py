from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.billing import PaymentAttempt
from app.models.user import User

SUCCESS_STATUSES = ("success", "paid", "completed")


@dataclass(slots=True, frozen=True)
class ProfitPeriod:
    revenue_kopecks: int
    partner_kopecks: int
    trials: int


@dataclass(slots=True, frozen=True)
class ProfitSnapshot:
    today: ProfitPeriod
    week: ProfitPeriod
    month: ProfitPeriod
    all_time: ProfitPeriod


@dataclass(slots=True, frozen=True)
class RevenuePoint:
    label: str
    revenue_kopecks: int


class AdminMetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @property
    def bot_id(self) -> int:
        return require_current_bot().id

    async def profit(self, trial_kinds: tuple[str, ...]) -> ProfitSnapshot:
        now = datetime.now(timezone.utc)
        return ProfitSnapshot(
            today=await self._profit_period(now - timedelta(days=1), trial_kinds),
            week=await self._profit_period(now - timedelta(days=7), trial_kinds),
            month=await self._profit_period(now - timedelta(days=30), trial_kinds),
            all_time=await self._profit_period(None, trial_kinds),
        )

    async def daily_revenue(self, *, days: int = 20) -> list[RevenuePoint]:
        if days < 1:
            raise ValueError("days must be positive")
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        points: list[RevenuePoint] = []
        for offset in range(days):
            left = start + timedelta(days=offset)
            right = left + timedelta(days=1)
            revenue = int(
                await self.session.scalar(
                    select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)).where(
                        PaymentAttempt.bot_id == self.bot_id,
                        PaymentAttempt.created_at >= left,
                        PaymentAttempt.created_at < right,
                        PaymentAttempt.status.in_(SUCCESS_STATUSES),
                    )
                ) or 0
            )
            points.append(RevenuePoint(label=left.strftime("%d.%m"), revenue_kopecks=revenue))
        return points

    async def export_user_ids(self, *, alive_only: bool) -> bytes:
        query = select(User.telegram_id).where(User.bot_id == self.bot_id)
        if alive_only:
            query = query.where(User.is_blocked.is_(False))
        query = query.order_by(User.id)
        result = await self.session.execute(query)
        values = [str(value) for value in result.scalars()]
        return ("\n".join(values) + ("\n" if values else "")).encode("utf-8")

    async def _profit_period(self, since: datetime | None, trial_kinds: tuple[str, ...]) -> ProfitPeriod:
        filters = [
            PaymentAttempt.bot_id == self.bot_id,
            PaymentAttempt.status.in_(SUCCESS_STATUSES),
        ]
        if since is not None:
            filters.append(PaymentAttempt.created_at >= since)
        revenue = int(
            await self.session.scalar(
                select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)).where(*filters)
            ) or 0
        )
        trial_filters = list(filters)
        if trial_kinds:
            trial_filters.append(PaymentAttempt.attempt_kind.in_(trial_kinds))
        else:
            trial_filters.append(False)
        trials = int(
            await self.session.scalar(select(func.count(PaymentAttempt.id)).where(*trial_filters)) or 0
        )
        return ProfitPeriod(
            revenue_kopecks=revenue,
            partner_kopecks=round(revenue * 0.60),
            trials=trials,
        )
