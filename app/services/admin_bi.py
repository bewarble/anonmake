from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
import csv

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Question, User
from app.models.billing import PaymentAttempt, Subscription
from app.models.crm import CrmEvent
from app.models.delivery import DeliveryOutbox
from app.models.marketing import SourceAttribution, TrafficSource


SUCCESS_STATUSES = ("success", "paid", "completed")
PERMANENT_DELIVERY_ERRORS = (
    "%bot was blocked%",
    "%chat not found%",
    "%user is deactivated%",
)


@dataclass(slots=True, frozen=True)
class PeriodPoint:
    label: str
    users: int
    organic: int
    revenue_kopecks: int
    profit_kopecks: int


@dataclass(slots=True, frozen=True)
class AdminStatistics:
    users_total: int
    users_active_30d: int
    users_unreachable: int
    today: int
    week: int
    month: int
    organic_today: int
    organic_week: int
    organic_month: int
    active_sources: int
    points: list[PeriodPoint]


@dataclass(slots=True, frozen=True)
class ProfitStatistics:
    revenue_today: int
    revenue_week: int
    revenue_month: int
    spend_today: int
    spend_week: int
    spend_month: int
    profit_today: int
    profit_week: int
    profit_month: int
    payments_today: int
    payments_week: int
    payments_month: int
    points: list[PeriodPoint]


class AdminBIService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def statistics(self) -> AdminStatistics:
        now = datetime.now(timezone.utc)
        day = now - timedelta(days=1)
        week = now - timedelta(days=7)
        month = now - timedelta(days=30)

        points = await self._daily_points(days=20)

        return AdminStatistics(
            users_total=await self._count_users(),
            users_active_30d=await self._active_users_since(month),
            users_unreachable=await self._unreachable_users(),
            today=await self._users_since(day),
            week=await self._users_since(week),
            month=await self._users_since(month),
            organic_today=await self._organic_users_since(day),
            organic_week=await self._organic_users_since(week),
            organic_month=await self._organic_users_since(month),
            active_sources=await self._active_sources(),
            points=points,
        )

    async def profit(self) -> ProfitStatistics:
        now = datetime.now(timezone.utc)
        day = now - timedelta(days=1)
        week = now - timedelta(days=7)
        month = now - timedelta(days=30)

        revenue_today = await self._revenue_since(day)
        revenue_week = await self._revenue_since(week)
        revenue_month = await self._revenue_since(month)

        spend_today = await self._spend_since(day)
        spend_week = await self._spend_since(week)
        spend_month = await self._spend_since(month)

        return ProfitStatistics(
            revenue_today=revenue_today,
            revenue_week=revenue_week,
            revenue_month=revenue_month,
            spend_today=spend_today,
            spend_week=spend_week,
            spend_month=spend_month,
            profit_today=revenue_today - spend_today,
            profit_week=revenue_week - spend_week,
            profit_month=revenue_month - spend_month,
            payments_today=await self._payments_since(day),
            payments_week=await self._payments_since(week),
            payments_month=await self._payments_since(month),
            points=await self._daily_points(days=20),
        )

    async def export_users_csv(self) -> bytes:
        result = await self.session.execute(
            select(
                User.id,
                User.telegram_id,
                User.username,
                User.first_name,
                User.created_at,
                TrafficSource.name,
            )
            .outerjoin(
                SourceAttribution,
                SourceAttribution.user_id == User.id,
            )
            .outerjoin(
                TrafficSource,
                TrafficSource.id == SourceAttribution.source_id,
            )
            .order_by(User.id)
        )

        stream = StringIO()
        writer = csv.writer(stream)
        writer.writerow(
            (
                "id",
                "telegram_id",
                "username",
                "first_name",
                "created_at",
                "source",
            )
        )
        for row in result.all():
            writer.writerow(row)

        return stream.getvalue().encode("utf-8-sig")

    async def source_report(self, source_id: int) -> dict[str, int | str] | None:
        source = await self.session.get(TrafficSource, source_id)
        if source is None:
            return None

        attributed = int(
            await self.session.scalar(
                select(func.count(SourceAttribution.id)).where(
                    SourceAttribution.source_id == source.id
                )
            )
            or 0
        )

        active = int(
            await self.session.scalar(
                select(func.count(func.distinct(SourceAttribution.user_id)))
                .join(
                    CrmEvent,
                    CrmEvent.user_id == SourceAttribution.user_id,
                )
                .where(
                    SourceAttribution.source_id == source.id,
                    CrmEvent.occurred_at >= datetime.now(timezone.utc)
                    - timedelta(days=30),
                )
            )
            or 0
        )

        cpc = source.spend_kopecks / source.clicks if source.clicks else 0
        cpa = source.spend_kopecks / attributed if attributed else 0

        return {
            "name": source.name,
            "clicks": source.clicks,
            "attributed": attributed,
            "active": active,
            "spend_kopecks": source.spend_kopecks,
            "cpc_kopecks": round(cpc),
            "cpa_kopecks": round(cpa),
        }

    async def _daily_points(self, *, days: int) -> list[PeriodPoint]:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        points: list[PeriodPoint] = []

        for offset in range(days):
            left = start + timedelta(days=offset)
            right = left + timedelta(days=1)
            users = await self._users_between(left, right)
            organic = await self._organic_users_between(left, right)
            revenue = await self._revenue_between(left, right)
            spend = await self._spend_between(left, right)
            points.append(
                PeriodPoint(
                    label=left.strftime("%d.%m"),
                    users=users,
                    organic=organic,
                    revenue_kopecks=revenue,
                    profit_kopecks=revenue - spend,
                )
            )
        return points

    async def _count_users(self) -> int:
        return int(
            await self.session.scalar(select(func.count(User.id))) or 0
        )

    async def _users_since(self, since: datetime) -> int:
        return int(
            await self.session.scalar(
                select(func.count(User.id)).where(User.created_at >= since)
            )
            or 0
        )

    async def _users_between(self, left: datetime, right: datetime) -> int:
        return int(
            await self.session.scalar(
                select(func.count(User.id)).where(
                    User.created_at >= left,
                    User.created_at < right,
                )
            )
            or 0
        )

    async def _active_users_since(self, since: datetime) -> int:
        return int(
            await self.session.scalar(
                select(func.count(func.distinct(CrmEvent.user_id))).where(
                    CrmEvent.occurred_at >= since
                )
            )
            or 0
        )

    async def _unreachable_users(self) -> int:
        condition = or_(
            *(DeliveryOutbox.last_error.ilike(pattern)
              for pattern in PERMANENT_DELIVERY_ERRORS)
        )
        return int(
            await self.session.scalar(
                select(func.count(func.distinct(User.id)))
                .join(
                    DeliveryOutbox,
                    DeliveryOutbox.chat_id == User.telegram_id,
                )
                .where(
                    DeliveryOutbox.status == "failed",
                    condition,
                )
            )
            or 0
        )

    async def _organic_users_since(self, since: datetime) -> int:
        return int(
            await self.session.scalar(
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
            or 0
        )

    async def _organic_users_between(
        self,
        left: datetime,
        right: datetime,
    ) -> int:
        return int(
            await self.session.scalar(
                select(func.count(User.id))
                .outerjoin(
                    SourceAttribution,
                    SourceAttribution.user_id == User.id,
                )
                .where(
                    User.created_at >= left,
                    User.created_at < right,
                    SourceAttribution.id.is_(None),
                )
            )
            or 0
        )

    async def _active_sources(self) -> int:
        return int(
            await self.session.scalar(
                select(func.count(TrafficSource.id)).where(
                    TrafficSource.is_active.is_(True)
                )
            )
            or 0
        )

    async def _payments_since(self, since: datetime) -> int:
        return int(
            await self.session.scalar(
                select(func.count(PaymentAttempt.id)).where(
                    PaymentAttempt.created_at >= since,
                    PaymentAttempt.status.in_(SUCCESS_STATUSES),
                )
            )
            or 0
        )

    async def _revenue_since(self, since: datetime) -> int:
        return int(
            await self.session.scalar(
                select(
                    func.coalesce(
                        func.sum(PaymentAttempt.amount_kopecks),
                        0,
                    )
                ).where(
                    PaymentAttempt.created_at >= since,
                    PaymentAttempt.status.in_(SUCCESS_STATUSES),
                )
            )
            or 0
        )

    async def _revenue_between(
        self,
        left: datetime,
        right: datetime,
    ) -> int:
        return int(
            await self.session.scalar(
                select(
                    func.coalesce(
                        func.sum(PaymentAttempt.amount_kopecks),
                        0,
                    )
                ).where(
                    PaymentAttempt.created_at >= left,
                    PaymentAttempt.created_at < right,
                    PaymentAttempt.status.in_(SUCCESS_STATUSES),
                )
            )
            or 0
        )

    async def _spend_since(self, since: datetime) -> int:
        return int(
            await self.session.scalar(
                select(
                    func.coalesce(
                        func.sum(TrafficSource.spend_kopecks),
                        0,
                    )
                ).where(TrafficSource.created_at >= since)
            )
            or 0
        )

    async def _spend_between(
        self,
        left: datetime,
        right: datetime,
    ) -> int:
        return int(
            await self.session.scalar(
                select(
                    func.coalesce(
                        func.sum(TrafficSource.spend_kopecks),
                        0,
                    )
                ).where(
                    TrafficSource.created_at >= left,
                    TrafficSource.created_at < right,
                )
            )
            or 0
        )
