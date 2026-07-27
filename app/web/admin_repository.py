from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Question, User
from app.models.admin import AdminAuditLog
from app.models.billing import PaymentAttempt, PaymentMethod, Subscription
from app.models.delivery import DeliveryOutbox
from app.models.marketing import SourceAttribution, TrafficSource
from app.models.reveal import RevealCheckout


SUCCESS_PAYMENT_STATUSES = ("success", "paid", "completed")
PERMANENT_DELIVERY_ERRORS = (
    "%bot was blocked%",
    "%chat not found%",
    "%user is deactivated%",
)


@dataclass(slots=True, frozen=True)
class Dashboard:
    users_total: int
    users_today: int
    users_dead: int
    questions_today: int
    answers_today: int
    active_vip: int
    active_cards: int
    revenue_today_kopecks: int
    revenue_total_kopecks: int
    delivery_pending: int
    delivery_failed: int
    active_sources: int


@dataclass(slots=True, frozen=True)
class UserRow:
    id: int
    telegram_id: int
    username: str | None
    first_name: str
    created_at: datetime
    vip_until: datetime | None
    source_name: str | None


@dataclass(slots=True, frozen=True)
class UserDetails:
    user: User
    subscription: Subscription | None
    payment_method: PaymentMethod | None
    source: TrafficSource | None
    sent_questions: int
    received_questions: int
    answers: int
    successful_payments: int
    revenue_kopecks: int
    reveals: int
    last_successful_payment: PaymentAttempt | None
    last_failed_payment: PaymentAttempt | None


@dataclass(slots=True, frozen=True)
class SourceRow:
    source: TrafficSource
    users_count: int
    cpa_kopecks: int | None


class WebAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def dashboard(self) -> Dashboard:
        now = datetime.now(timezone.utc)
        day = now - timedelta(days=1)

        users_total = await self._count(User)
        users_today = await self._count(User, User.created_at >= day)

        dead_condition = or_(
            *(
                DeliveryOutbox.last_error.ilike(pattern)
                for pattern in PERMANENT_DELIVERY_ERRORS
            )
        )
        users_dead = int(
            await self.session.scalar(
                select(func.count(func.distinct(User.id)))
                .join(
                    DeliveryOutbox,
                    DeliveryOutbox.chat_id == User.telegram_id,
                )
                .where(
                    DeliveryOutbox.status == "failed",
                    dead_condition,
                )
            )
            or 0
        )

        questions_today = await self._count(
            Question,
            Question.created_at >= day,
        )
        answers_today = await self._count(
            Answer,
            Answer.created_at >= day,
        )
        active_vip = await self._count(
            Subscription,
            Subscription.access_until.is_not(None),
            Subscription.access_until > now,
        )
        active_cards = await self._count(
            PaymentMethod,
            PaymentMethod.is_active.is_(True),
            PaymentMethod.is_recurrent.is_(True),
            PaymentMethod.binding_id.is_not(None),
            PaymentMethod.blocked_at.is_(None),
        )

        revenue_today = await self._revenue(
            PaymentAttempt.created_at >= day
        )
        revenue_total = await self._revenue()

        delivery_pending = await self._count(
            DeliveryOutbox,
            DeliveryOutbox.status.in_(("pending", "processing")),
        )
        delivery_failed = await self._count(
            DeliveryOutbox,
            DeliveryOutbox.status == "failed",
        )
        active_sources = await self._count(
            TrafficSource,
            TrafficSource.is_active.is_(True),
        )

        return Dashboard(
            users_total=users_total,
            users_today=users_today,
            users_dead=users_dead,
            questions_today=questions_today,
            answers_today=answers_today,
            active_vip=active_vip,
            active_cards=active_cards,
            revenue_today_kopecks=revenue_today,
            revenue_total_kopecks=revenue_total,
            delivery_pending=delivery_pending,
            delivery_failed=delivery_failed,
            active_sources=active_sources,
        )

    async def users(
        self,
        *,
        query: str,
        page: int,
        page_size: int,
    ) -> tuple[list[UserRow], int]:
        filters = []
        cleaned = query.strip().lstrip("@")
        if cleaned:
            if cleaned.isdigit():
                numeric = int(cleaned)
                filters.append(
                    or_(
                        User.id == numeric,
                        User.telegram_id == numeric,
                    )
                )
            else:
                pattern = f"%{cleaned}%"
                filters.append(
                    or_(
                        User.username.ilike(pattern),
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                    )
                )

        total = int(
            await self.session.scalar(
                select(func.count(User.id)).where(*filters)
            )
            or 0
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
            )
            .outerjoin(
                Subscription,
                Subscription.user_id == User.id,
            )
            .outerjoin(
                SourceAttribution,
                SourceAttribution.user_id == User.id,
            )
            .outerjoin(
                TrafficSource,
                TrafficSource.id == SourceAttribution.source_id,
            )
            .where(*filters)
            .order_by(User.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )

        rows = [
            UserRow(
                id=row.id,
                telegram_id=row.telegram_id,
                username=row.username,
                first_name=row.first_name,
                created_at=row.created_at,
                vip_until=row.access_until,
                source_name=row.source_name,
            )
            for row in result
        ]
        return rows, total

    async def user_details(self, user_id: int) -> UserDetails | None:
        user = await self.session.get(User, user_id)
        if user is None:
            return None

        subscription = await self.session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        payment_method = await self.session.scalar(
            select(PaymentMethod).where(PaymentMethod.user_id == user.id)
        )
        source = await self.session.scalar(
            select(TrafficSource)
            .join(
                SourceAttribution,
                SourceAttribution.source_id == TrafficSource.id,
            )
            .where(SourceAttribution.user_id == user.id)
        )

        sent_questions = await self._count(
            Question,
            Question.sender_id == user.id,
        )
        received_questions = await self._count(
            Question,
            Question.recipient_id == user.id,
        )
        answers = int(
            await self.session.scalar(
                select(func.count(Answer.id))
                .join(Question, Answer.question_id == Question.id)
                .where(Question.recipient_id == user.id)
            )
            or 0
        )
        successful_payments = int(
            await self.session.scalar(
                select(func.count(PaymentAttempt.id))
                .join(
                    Subscription,
                    PaymentAttempt.subscription_id == Subscription.id,
                )
                .where(
                    Subscription.user_id == user.id,
                    PaymentAttempt.status.in_(SUCCESS_PAYMENT_STATUSES),
                )
            )
            or 0
        )
        revenue_kopecks = int(
            await self.session.scalar(
                select(
                    func.coalesce(
                        func.sum(PaymentAttempt.amount_kopecks),
                        0,
                    )
                )
                .join(
                    Subscription,
                    PaymentAttempt.subscription_id == Subscription.id,
                )
                .where(
                    Subscription.user_id == user.id,
                    PaymentAttempt.status.in_(SUCCESS_PAYMENT_STATUSES),
                )
            )
            or 0
        )
        reveals = await self._count(
            RevealCheckout,
            RevealCheckout.buyer_id == user.id,
            RevealCheckout.status.in_(SUCCESS_PAYMENT_STATUSES),
        )

        return UserDetails(
            user=user,
            subscription=subscription,
            payment_method=payment_method,
            source=source,
            sent_questions=sent_questions,
            received_questions=received_questions,
            answers=answers,
            successful_payments=successful_payments,
            revenue_kopecks=revenue_kopecks,
            reveals=reveals,
            last_successful_payment=await self.session.scalar(
                select(PaymentAttempt)
                .where(
                    PaymentAttempt.subscription_id == (
                        subscription.id if subscription else -1
                    ),
                    PaymentAttempt.status == "success",
                )
                .order_by(PaymentAttempt.id.desc())
                .limit(1)
            ),
            last_failed_payment=await self.session.scalar(
                select(PaymentAttempt)
                .where(
                    PaymentAttempt.subscription_id == (
                        subscription.id if subscription else -1
                    ),
                    PaymentAttempt.status.in_(
                        ("failed", "insufficient_funds", "pending")
                    ),
                )
                .order_by(PaymentAttempt.id.desc())
                .limit(1)
            ),
        )

    async def payments(
        self,
        *,
        page: int,
        page_size: int,
        query: str = "",
        status: str = "",
        kind: str = "",
    ):
        filters = []
        cleaned = query.strip().lstrip("@")
        if cleaned:
            pattern = f"%{cleaned}%"
            if cleaned.isdigit():
                numeric = int(cleaned)
                filters.append(
                    or_(
                        User.telegram_id == numeric,
                        User.id == numeric,
                        PaymentAttempt.id == numeric,
                    )
                )
            else:
                filters.append(
                    or_(
                        User.username.ilike(pattern),
                        PaymentAttempt.customer_operation_id.ilike(pattern),
                        PaymentAttempt.transaction_id.ilike(pattern),
                        PaymentMethod.binding_id.ilike(pattern),
                    )
                )

        if status:
            filters.append(PaymentAttempt.status == status)
        if kind:
            filters.append(PaymentAttempt.attempt_kind == kind)

        total = int(
            await self.session.scalar(
                select(func.count(PaymentAttempt.id))
                .join(
                    Subscription,
                    PaymentAttempt.subscription_id == Subscription.id,
                )
                .join(User, Subscription.user_id == User.id)
                .outerjoin(PaymentMethod, PaymentMethod.user_id == User.id)
                .where(*filters)
            )
            or 0
        )

        result = await self.session.execute(
            select(PaymentAttempt, Subscription, User, PaymentMethod)
            .join(
                Subscription,
                PaymentAttempt.subscription_id == Subscription.id,
            )
            .join(User, Subscription.user_id == User.id)
            .outerjoin(PaymentMethod, PaymentMethod.user_id == User.id)
            .where(*filters)
            .order_by(PaymentAttempt.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        return result.all(), total

    async def payment_details(self, attempt_id: int):
        result = await self.session.execute(
            select(PaymentAttempt, Subscription, User, PaymentMethod)
            .join(
                Subscription,
                PaymentAttempt.subscription_id == Subscription.id,
            )
            .join(User, Subscription.user_id == User.id)
            .outerjoin(PaymentMethod, PaymentMethod.user_id == User.id)
            .where(PaymentAttempt.id == attempt_id)
        )
        return result.one_or_none()

    async def sources(self) -> list[SourceRow]:
        users_count = func.count(SourceAttribution.id).label("users_count")
        result = await self.session.execute(
            select(TrafficSource, users_count)
            .outerjoin(
                SourceAttribution,
                SourceAttribution.source_id == TrafficSource.id,
            )
            .group_by(TrafficSource.id)
            .order_by(TrafficSource.id.desc())
        )

        rows: list[SourceRow] = []
        for source, count in result.all():
            count = int(count or 0)
            cpa = (
                round(source.spend_kopecks / count)
                if count
                else None
            )
            rows.append(
                SourceRow(
                    source=source,
                    users_count=count,
                    cpa_kopecks=cpa,
                )
            )
        return rows

    async def delivery(
        self,
        *,
        page: int,
        page_size: int,
    ):
        total = await self._count(DeliveryOutbox)
        result = await self.session.execute(
            select(DeliveryOutbox)
            .order_by(DeliveryOutbox.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), total

    async def audit(
        self,
        *,
        page: int,
        page_size: int,
    ):
        total = await self._count(AdminAuditLog)
        result = await self.session.execute(
            select(AdminAuditLog)
            .order_by(AdminAuditLog.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), total

    async def _revenue(self, *conditions) -> int:
        value = await self.session.scalar(
            select(
                func.coalesce(
                    func.sum(PaymentAttempt.amount_kopecks),
                    0,
                )
            ).where(
                PaymentAttempt.status.in_(SUCCESS_PAYMENT_STATUSES),
                *conditions,
            )
        )
        return int(value or 0)

    async def _count(self, model, *conditions) -> int:
        value = await self.session.scalar(
            select(func.count(model.id)).where(*conditions)
        )
        return int(value or 0)
