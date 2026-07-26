from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Question, User
from app.models.billing import PaymentAttempt, Subscription
from app.models.delivery import DeliveryOutbox

UserFilter = Literal["recent", "vip", "paid", "inactive"]
PaymentFilter = Literal["all", "success", "failed", "pending"]
SubscriptionFilter = Literal["active", "renewal", "cancelled", "expired"]


@dataclass(slots=True, frozen=True)
class AdminOverview:
    users_total: int
    users_today: int
    questions_today: int
    answers_today: int
    active_vip: int
    payments_today: int
    revenue_today_kopecks: int
    delivery_pending: int
    delivery_failed: int


@dataclass(slots=True, frozen=True)
class PaymentRow:
    attempt: PaymentAttempt
    subscription: Subscription
    user: User


@dataclass(slots=True, frozen=True)
class SubscriptionRow:
    subscription: Subscription
    user: User


class AdminControlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self) -> AdminOverview:
        now = datetime.now(timezone.utc)
        today = now - timedelta(hours=24)

        return AdminOverview(
            users_total=await self._count(User),
            users_today=await self._count_since(User, today),
            questions_today=await self._count_since(Question, today),
            answers_today=await self._count_since(Answer, today),
            active_vip=await self._count_active_vip(now),
            payments_today=await self._count_payments_since(today),
            revenue_today_kopecks=await self._revenue_since(today),
            delivery_pending=await self._count_delivery(
                ("pending", "processing", "retry")
            ),
            delivery_failed=await self._count_delivery(("failed",)),
        )

    async def users(
        self,
        *,
        filter_name: UserFilter,
        page: int,
        page_size: int = 8,
    ) -> tuple[list[User], bool]:
        query = select(User).order_by(User.id.desc())

        if filter_name == "vip":
            now = datetime.now(timezone.utc)
            query = (
                query.join(Subscription, Subscription.user_id == User.id)
                .where(Subscription.access_until > now)
            )
        elif filter_name == "paid":
            query = (
                query.join(Subscription, Subscription.user_id == User.id)
                .join(
                    PaymentAttempt,
                    PaymentAttempt.subscription_id == Subscription.id,
                )
                .where(
                    PaymentAttempt.status.in_(
                        ("success", "paid", "completed")
                    )
                )
                .distinct()
            )
        elif filter_name == "inactive":
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            query = query.where(User.created_at < cutoff)

        offset = max(page, 0) * page_size
        result = await self.session.execute(
            query.offset(offset).limit(page_size + 1)
        )
        items = list(result.scalars())
        return items[:page_size], len(items) > page_size

    async def payments(
        self,
        *,
        filter_name: PaymentFilter,
        page: int,
        page_size: int = 8,
    ) -> tuple[list[PaymentRow], bool]:
        query = (
            select(PaymentAttempt, Subscription, User)
            .join(
                Subscription,
                PaymentAttempt.subscription_id == Subscription.id,
            )
            .join(User, Subscription.user_id == User.id)
            .order_by(PaymentAttempt.id.desc())
        )

        if filter_name == "success":
            query = query.where(
                PaymentAttempt.status.in_(("success", "paid", "completed"))
            )
        elif filter_name == "failed":
            query = query.where(
                PaymentAttempt.status.in_(("failed", "declined", "error"))
            )
        elif filter_name == "pending":
            query = query.where(
                PaymentAttempt.status.in_(("pending", "created", "processing"))
            )

        offset = max(page, 0) * page_size
        result = await self.session.execute(
            query.offset(offset).limit(page_size + 1)
        )
        rows = [
            PaymentRow(attempt=attempt, subscription=subscription, user=user)
            for attempt, subscription, user in result.all()
        ]
        return rows[:page_size], len(rows) > page_size

    async def subscriptions(
        self,
        *,
        filter_name: SubscriptionFilter,
        page: int,
        page_size: int = 8,
    ) -> tuple[list[SubscriptionRow], bool]:
        now = datetime.now(timezone.utc)
        query = (
            select(Subscription, User)
            .join(User, Subscription.user_id == User.id)
            .order_by(Subscription.id.desc())
        )

        if filter_name == "active":
            query = query.where(Subscription.access_until > now)
        elif filter_name == "renewal":
            query = query.where(
                Subscription.auto_renew.is_(True),
                Subscription.next_charge_at.is_not(None),
                Subscription.cancelled_at.is_(None),
            )
        elif filter_name == "cancelled":
            query = query.where(
                or_(
                    Subscription.cancelled_at.is_not(None),
                    Subscription.auto_renew.is_(False),
                )
            )
        elif filter_name == "expired":
            query = query.where(
                Subscription.access_until.is_not(None),
                Subscription.access_until <= now,
            )

        offset = max(page, 0) * page_size
        result = await self.session.execute(
            query.offset(offset).limit(page_size + 1)
        )
        rows = [
            SubscriptionRow(subscription=subscription, user=user)
            for subscription, user in result.all()
        ]
        return rows[:page_size], len(rows) > page_size

    async def payment_details(self, attempt_id: int) -> PaymentRow | None:
        result = await self.session.execute(
            select(PaymentAttempt, Subscription, User)
            .join(
                Subscription,
                PaymentAttempt.subscription_id == Subscription.id,
            )
            .join(User, Subscription.user_id == User.id)
            .where(PaymentAttempt.id == attempt_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        attempt, subscription, user = row
        return PaymentRow(
            attempt=attempt,
            subscription=subscription,
            user=user,
        )

    async def _count(self, model) -> int:
        value = await self.session.scalar(select(func.count(model.id)))
        return int(value or 0)

    async def _count_since(self, model, since: datetime) -> int:
        value = await self.session.scalar(
            select(func.count(model.id)).where(model.created_at >= since)
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

    async def _count_payments_since(self, since: datetime) -> int:
        value = await self.session.scalar(
            select(func.count(PaymentAttempt.id)).where(
                PaymentAttempt.created_at >= since,
                PaymentAttempt.status.in_(("success", "paid", "completed")),
            )
        )
        return int(value or 0)

    async def _revenue_since(self, since: datetime) -> int:
        value = await self.session.scalar(
            select(
                func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)
            ).where(
                PaymentAttempt.created_at >= since,
                PaymentAttempt.status.in_(("success", "paid", "completed")),
            )
        )
        return int(value or 0)

    async def _count_delivery(self, statuses: tuple[str, ...]) -> int:
        value = await self.session.scalar(
            select(func.count(DeliveryOutbox.id)).where(
                DeliveryOutbox.status.in_(statuses)
            )
        )
        return int(value or 0)
