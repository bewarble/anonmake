from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import PaymentAttempt, PaymentMethod
from app.models.delivery import DeliveryOutbox
from app.models.user import User

SUCCESS_STATUSES = ("success", "paid", "completed")
PERMANENT_ERRORS = (
    "%bot was blocked%",
    "%chat not found%",
    "%user is deactivated%",
)


@dataclass(slots=True, frozen=True)
class StatisticsSnapshot:
    users_total: int
    users_alive: int
    users_dead: int
    today: int
    week: int
    month: int
    organic_today: int
    organic_week: int
    organic_month: int
    active_cards: int


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


class AdminMetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def statistics(self) -> StatisticsSnapshot:
        now = datetime.now(timezone.utc)
        day = now - timedelta(days=1)
        week = now - timedelta(days=7)
        month = now - timedelta(days=30)

        total = int(
            await self.session.scalar(select(func.count(User.id))) or 0
        )
        dead = await self._dead_users()

        return StatisticsSnapshot(
            users_total=total,
            users_alive=max(total - dead, 0),
            users_dead=dead,
            today=await self._users_since(day),
            week=await self._users_since(week),
            month=await self._users_since(month),
            organic_today=await self._organic_since(day),
            organic_week=await self._organic_since(week),
            organic_month=await self._organic_since(month),
            active_cards=await self._active_cards(),
        )

    async def profit(self, trial_kinds: tuple[str, ...]) -> ProfitSnapshot:
        now = datetime.now(timezone.utc)
        return ProfitSnapshot(
            today=await self._profit_period(now - timedelta(days=1), trial_kinds),
            week=await self._profit_period(now - timedelta(days=7), trial_kinds),
            month=await self._profit_period(now - timedelta(days=30), trial_kinds),
            all_time=await self._profit_period(None, trial_kinds),
        )

    async def export_user_ids(self, *, alive_only: bool) -> bytes:
        query = select(User.telegram_id).order_by(User.id)

        if alive_only:
            dead_users = (
                select(User.id)
                .join(
                    DeliveryOutbox,
                    DeliveryOutbox.chat_id == User.telegram_id,
                )
                .where(
                    DeliveryOutbox.status == "failed",
                    or_(
                        *(DeliveryOutbox.last_error.ilike(pattern)
                          for pattern in PERMANENT_ERRORS)
                    ),
                )
            )
            query = query.where(User.id.not_in(dead_users))

        result = await self.session.execute(query)
        values = [str(value) for value in result.scalars()]
        return ("\n".join(values) + ("\n" if values else "")).encode("utf-8")

    async def _dead_users(self) -> int:
        value = await self.session.scalar(
            select(func.count(func.distinct(User.id)))
            .join(
                DeliveryOutbox,
                DeliveryOutbox.chat_id == User.telegram_id,
            )
            .where(
                DeliveryOutbox.status == "failed",
                or_(
                    *(DeliveryOutbox.last_error.ilike(pattern)
                      for pattern in PERMANENT_ERRORS)
                ),
            )
        )
        return int(value or 0)

    async def _users_since(self, since: datetime) -> int:
        value = await self.session.scalar(
            select(func.count(User.id)).where(User.created_at >= since)
        )
        return int(value or 0)

    async def _organic_since(self, since: datetime) -> int:
        from app.models.marketing import SourceAttribution

        value = await self.session.scalar(
            select(func.count(User.id))
            .outerjoin(
                SourceAttribution,
                SourceAttribution.user_id == User.id,
            )
            .where(
                User.created_at >= since,
                SourceAttribution.id.is_(None),
            )
        )
        return int(value or 0)

    async def _active_cards(self) -> int:
        value = await self.session.scalar(
            select(func.count(PaymentMethod.id)).where(
                PaymentMethod.is_active.is_(True),
                PaymentMethod.is_recurrent.is_(True),
                PaymentMethod.binding_id.is_not(None),
                PaymentMethod.blocked_at.is_(None),
            )
        )
        return int(value or 0)

    async def _profit_period(
        self,
        since: datetime | None,
        trial_kinds: tuple[str, ...],
    ) -> ProfitPeriod:
        filters = [PaymentAttempt.status.in_(SUCCESS_STATUSES)]
        if since is not None:
            filters.append(PaymentAttempt.created_at >= since)

        revenue = int(
            await self.session.scalar(
                select(
                    func.coalesce(
                        func.sum(PaymentAttempt.amount_kopecks),
                        0,
                    )
                ).where(*filters)
            )
            or 0
        )

        trials = int(
            await self.session.scalar(
                select(func.count(PaymentAttempt.id)).where(
                    *filters,
                    PaymentAttempt.attempt_kind.in_(trial_kinds),
                )
            )
            or 0
        )

        return ProfitPeriod(
            revenue_kopecks=revenue,
            partner_kopecks=round(revenue * 0.60),
            trials=trials,
        )
