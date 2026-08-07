from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.billing import PaymentMethod
from app.models.delivery import DeliveryOutbox
from app.models.marketing import SourceAttribution
from app.models.user import User

PERMANENT_ERRORS = (
    "%bot was blocked%",
    "%chat not found%",
    "%user is deactivated%",
)


@dataclass(slots=True, frozen=True)
class DailyStatisticsPoint:
    label: str
    joined: int
    blocked: int


@dataclass(slots=True, frozen=True)
class StatisticsStage25:
    users_total: int
    users_alive: int
    users_dead: int
    today: int
    week: int
    month: int
    all_time: int
    organic_today: int
    organic_week: int
    organic_month: int
    organic_all_time: int
    active_cards: int
    points: list[DailyStatisticsPoint]


class AdminStatisticsStage25Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def snapshot(self, *, days: int = 20) -> StatisticsStage25:
        bot_id = require_current_bot().id
        now = datetime.now(timezone.utc)
        day = now - timedelta(days=1)
        week = now - timedelta(days=7)
        month = now - timedelta(days=30)

        users_total = await self._users_count(bot_id)
        users_dead = await self._dead_users_count(bot_id)

        return StatisticsStage25(
            users_total=users_total,
            users_alive=max(users_total - users_dead, 0),
            users_dead=users_dead,
            today=await self._users_since(bot_id, day),
            week=await self._users_since(bot_id, week),
            month=await self._users_since(bot_id, month),
            all_time=users_total,
            organic_today=await self._organic_since(bot_id, day),
            organic_week=await self._organic_since(bot_id, week),
            organic_month=await self._organic_since(bot_id, month),
            organic_all_time=await self._organic_all_time(bot_id),
            active_cards=await self._active_cards(bot_id),
            points=await self._daily_points(bot_id, days=days),
        )

    async def _users_count(self, bot_id: int) -> int:
        value = await self.session.scalar(
            select(func.count(User.id)).where(User.bot_id == bot_id)
        )
        return int(value or 0)

    async def _users_since(self, bot_id: int, since: datetime) -> int:
        value = await self.session.scalar(
            select(func.count(User.id)).where(
                User.bot_id == bot_id,
                User.created_at >= since,
            )
        )
        return int(value or 0)

    async def _dead_users_count(self, bot_id: int) -> int:
        value = await self.session.scalar(
            select(func.count(func.distinct(User.id)))
            .join(
                DeliveryOutbox,
                (DeliveryOutbox.chat_id == User.telegram_id)
                & (DeliveryOutbox.bot_id == User.bot_id),
            )
            .where(
                User.bot_id == bot_id,
                DeliveryOutbox.bot_id == bot_id,
                DeliveryOutbox.status == "failed",
                self._permanent_error_condition(),
            )
        )
        return int(value or 0)

    async def _organic_since(self, bot_id: int, since: datetime) -> int:
        value = await self.session.scalar(
            select(func.count(User.id))
            .outerjoin(
                SourceAttribution,
                SourceAttribution.user_id == User.id,
            )
            .where(
                User.bot_id == bot_id,
                User.created_at >= since,
                SourceAttribution.id.is_(None),
            )
        )
        return int(value or 0)

    async def _organic_all_time(self, bot_id: int) -> int:
        value = await self.session.scalar(
            select(func.count(User.id))
            .outerjoin(
                SourceAttribution,
                SourceAttribution.user_id == User.id,
            )
            .where(
                User.bot_id == bot_id,
                SourceAttribution.id.is_(None),
            )
        )
        return int(value or 0)

    async def _active_cards(self, bot_id: int) -> int:
        value = await self.session.scalar(
            select(func.count(PaymentMethod.id)).where(
                PaymentMethod.bot_id == bot_id,
                PaymentMethod.is_active.is_(True),
                PaymentMethod.is_recurrent.is_(True),
                PaymentMethod.binding_id.is_not(None),
                PaymentMethod.blocked_at.is_(None),
            )
        )
        return int(value or 0)

    async def _daily_points(self, bot_id: int, *, days: int) -> list[DailyStatisticsPoint]:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days - 1)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        result: list[DailyStatisticsPoint] = []
        for offset in range(days):
            left = start + timedelta(days=offset)
            right = left + timedelta(days=1)

            joined = int(
                await self.session.scalar(
                    select(func.count(User.id)).where(
                        User.bot_id == bot_id,
                        User.created_at >= left,
                        User.created_at < right,
                    )
                )
                or 0
            )

            first_permanent_failure = (
                select(
                    User.id.label("user_id"),
                    func.min(DeliveryOutbox.updated_at).label("blocked_at"),
                )
                .join(
                    DeliveryOutbox,
                    (DeliveryOutbox.chat_id == User.telegram_id)
                    & (DeliveryOutbox.bot_id == User.bot_id),
                )
                .where(
                    User.bot_id == bot_id,
                    DeliveryOutbox.bot_id == bot_id,
                    DeliveryOutbox.status == "failed",
                    self._permanent_error_condition(),
                )
                .group_by(User.id)
                .subquery()
            )

            blocked = int(
                await self.session.scalar(
                    select(func.count(first_permanent_failure.c.user_id)).where(
                        first_permanent_failure.c.blocked_at >= left,
                        first_permanent_failure.c.blocked_at < right,
                    )
                )
                or 0
            )

            result.append(
                DailyStatisticsPoint(
                    label=left.strftime("%d.%m"),
                    joined=joined,
                    blocked=blocked,
                )
            )

        return result

    @staticmethod
    def _permanent_error_condition():
        return or_(
            *(
                DeliveryOutbox.last_error.ilike(pattern)
                for pattern in PERMANENT_ERRORS
            )
        )
