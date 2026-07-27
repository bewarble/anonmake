from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import User
from app.models.billing import PaymentAttempt, Subscription
from app.models.crm import CrmEvent
from app.models.delivery import DeliveryOutbox
from app.models.marketing import Broadcast, SourceAttribution, TrafficSource

SUCCESS_STATUSES = ("success", "paid", "completed")
PERMANENT_ERRORS = (
    "%bot was blocked%",
    "%chat not found%",
    "%user is deactivated%",
)


@dataclass(slots=True, frozen=True)
class ChartPoint:
    label: str
    registrations: int
    blocked: int
    revenue_kopecks: int


@dataclass(slots=True, frozen=True)
class CrmUserRow:
    id: int
    telegram_id: int
    username: str | None
    first_name: str
    created_at: datetime
    vip_until: datetime | None
    source_name: str | None
    is_dead: bool


@dataclass(slots=True, frozen=True)
class SourceDetails:
    source: TrafficSource
    users_count: int
    active_users_30d: int
    vip_users: int
    cpa_kopecks: int | None
    vip_cpa_kopecks: int | None


class WebCrmRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def permanent_error_condition():
        return or_(
            *(DeliveryOutbox.last_error.ilike(pattern) for pattern in PERMANENT_ERRORS)
        )

    async def chart(self, days: int = 30) -> list[ChartPoint]:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        first_failure = (
            select(
                DeliveryOutbox.chat_id.label("chat_id"),
                func.min(DeliveryOutbox.updated_at).label("blocked_at"),
            )
            .where(
                DeliveryOutbox.status == "failed",
                self.permanent_error_condition(),
            )
            .group_by(DeliveryOutbox.chat_id)
            .subquery()
        )

        points: list[ChartPoint] = []
        for offset in range(days):
            left = start + timedelta(days=offset)
            right = left + timedelta(days=1)

            registrations = int(
                await self.session.scalar(
                    select(func.count(User.id)).where(
                        User.created_at >= left,
                        User.created_at < right,
                    )
                ) or 0
            )
            blocked = int(
                await self.session.scalar(
                    select(func.count(first_failure.c.chat_id)).where(
                        first_failure.c.blocked_at >= left,
                        first_failure.c.blocked_at < right,
                    )
                ) or 0
            )
            revenue = int(
                await self.session.scalar(
                    select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0))
                    .where(
                        PaymentAttempt.status.in_(SUCCESS_STATUSES),
                        PaymentAttempt.created_at >= left,
                        PaymentAttempt.created_at < right,
                    )
                ) or 0
            )
            points.append(
                ChartPoint(
                    label=left.strftime("%d.%m"),
                    registrations=registrations,
                    blocked=blocked,
                    revenue_kopecks=revenue,
                )
            )
        return points

    async def users(
        self,
        *,
        query: str,
        vip: str,
        health: str,
        source_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CrmUserRow], int]:
        now = datetime.now(timezone.utc)
        filters = []
        cleaned = query.strip().lstrip("@")

        if cleaned:
            if cleaned.isdigit():
                numeric = int(cleaned)
                filters.append(or_(User.id == numeric, User.telegram_id == numeric))
            else:
                pattern = f"%{cleaned}%"
                filters.append(
                    or_(
                        User.username.ilike(pattern),
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                    )
                )

        vip_subscription = aliased(Subscription)

        active_vip = exists(
            select(vip_subscription.id)
            .select_from(vip_subscription)
            .where(
                vip_subscription.user_id == User.id,
                vip_subscription.access_until.is_not(None),
                vip_subscription.access_until > now,
            )
        )
        if vip == "active":
            filters.append(active_vip)
        elif vip == "inactive":
            filters.append(~active_vip)

        failed_delivery = aliased(DeliveryOutbox)

        dead_user = exists(
            select(failed_delivery.id)
            .select_from(failed_delivery)
            .where(
                failed_delivery.chat_id == User.telegram_id,
                failed_delivery.status == "failed",
                or_(
                    *(
                        failed_delivery.last_error.ilike(pattern)
                        for pattern in PERMANENT_ERRORS
                    )
                ),
            )
        )
        if health == "alive":
            filters.append(~dead_user)
        elif health == "dead":
            filters.append(dead_user)

        if source_id is not None:
            source_attribution_filter = aliased(SourceAttribution)

            filters.append(
                exists(
                    select(source_attribution_filter.id)
                    .select_from(source_attribution_filter)
                    .where(
                        source_attribution_filter.user_id == User.id,
                        source_attribution_filter.source_id == source_id,
                    )
                )
            )

        total = int(
            await self.session.scalar(
                select(func.count(User.id)).where(*filters)
            ) or 0
        )

        source_name = TrafficSource.name.label("source_name")
        result = await self.session.execute(
            select(
                User.id,
                User.telegram_id,
                User.username,
                User.first_name,
                User.created_at,
                Subscription.access_until,
                source_name,
                dead_user.label("is_dead"),
            )
            .outerjoin(Subscription, Subscription.user_id == User.id)
            .outerjoin(SourceAttribution, SourceAttribution.user_id == User.id)
            .outerjoin(TrafficSource, TrafficSource.id == SourceAttribution.source_id)
            .where(*filters)
            .order_by(User.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        rows = [
            CrmUserRow(
                id=row.id,
                telegram_id=row.telegram_id,
                username=row.username,
                first_name=row.first_name,
                created_at=row.created_at,
                vip_until=row.access_until,
                source_name=row.source_name,
                is_dead=bool(row.is_dead),
            )
            for row in result
        ]
        return rows, total

    async def sources(self) -> list[TrafficSource]:
        result = await self.session.execute(
            select(TrafficSource).order_by(TrafficSource.id.desc())
        )
        return list(result.scalars())

    async def user_timeline(self, user_id: int, limit: int = 100) -> list[CrmEvent]:
        result = await self.session.execute(
            select(CrmEvent)
            .where(CrmEvent.user_id == user_id)
            .order_by(CrmEvent.occurred_at.desc(), CrmEvent.id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def source_details(self, source_id: int) -> SourceDetails | None:
        source = await self.session.get(TrafficSource, source_id)
        if source is None:
            return None

        users_count = int(
            await self.session.scalar(
                select(func.count(SourceAttribution.id)).where(
                    SourceAttribution.source_id == source.id
                )
            ) or 0
        )
        active_users_30d = int(
            await self.session.scalar(
                select(func.count(func.distinct(SourceAttribution.user_id)))
                .join(CrmEvent, CrmEvent.user_id == SourceAttribution.user_id)
                .where(
                    SourceAttribution.source_id == source.id,
                    CrmEvent.occurred_at >= datetime.now(timezone.utc) - timedelta(days=30),
                )
            ) or 0
        )
        now = datetime.now(timezone.utc)
        vip_users = int(
            await self.session.scalar(
                select(func.count(func.distinct(SourceAttribution.user_id)))
                .join(Subscription, Subscription.user_id == SourceAttribution.user_id)
                .where(
                    SourceAttribution.source_id == source.id,
                    Subscription.access_until.is_not(None),
                    Subscription.access_until > now,
                )
            ) or 0
        )
        return SourceDetails(
            source=source,
            users_count=users_count,
            active_users_30d=active_users_30d,
            vip_users=vip_users,
            cpa_kopecks=round(source.spend_kopecks / users_count) if users_count else None,
            vip_cpa_kopecks=round(source.spend_kopecks / vip_users) if vip_users else None,
        )

    async def broadcasts(self, page: int, page_size: int):
        total = int(await self.session.scalar(select(func.count(Broadcast.id))) or 0)
        result = await self.session.execute(
            select(Broadcast)
            .order_by(Broadcast.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), total
