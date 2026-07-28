from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Question, User
from app.models.billing import PaymentAttempt, PaymentMethod, Subscription
from app.models.crm import CrmEvent, CrmNote, CrmTag, CrmUserTag
from app.models.delivery import DeliveryOutbox
from app.models.marketing import Broadcast, SourceAttribution, TrafficSource

SUCCESS_STATUSES = ("success", "paid", "completed")
PERMANENT_ERRORS = (
    "%bot was blocked%",
    "%chat not found%",
    "%user is deactivated%",
)


@dataclass(slots=True, frozen=True)
class ComparisonMetric:
    current: int
    previous: int

    @property
    def delta_percent(self) -> float | None:
        if self.previous == 0:
            return None if self.current == 0 else 100.0
        return round((self.current - self.previous) / self.previous * 100, 1)


@dataclass(slots=True, frozen=True)
class DashboardSnapshot:
    users: ComparisonMetric
    questions: ComparisonMetric
    answers: ComparisonMetric
    revenue_kopecks: ComparisonMetric
    trials: ComparisonMetric
    rebills: ComparisonMetric
    successful_rebill_rate: float
    active_vip: int
    active_cards: int
    dead_users: int
    arpu_kopecks: int


@dataclass(slots=True, frozen=True)
class ChartPoint:
    label: str
    users: int
    blocked: int
    questions: int
    answers: int
    revenue_kopecks: int


@dataclass(slots=True, frozen=True)
class UserRow:
    id: int
    telegram_id: int
    username: str | None
    first_name: str
    created_at: datetime
    last_event_at: datetime | None
    source_name: str | None
    vip_until: datetime | None
    questions_sent: int
    answers_count: int
    is_dead: bool


@dataclass(slots=True, frozen=True)
class SourceRow:
    source: TrafficSource
    users: int
    vip_users: int
    paid_users: int
    payments: int
    revenue_kopecks: int
    cpa_kopecks: int | None
    vip_cpa_kopecks: int | None
    payment_cpa_kopecks: int | None
    registration_conversion_percent: float | None
    payment_conversion_percent: float | None
    roi_percent: float | None


class Stage29Repository:
    def __init__(self, session: AsyncSession, bot_id: int | None = None) -> None:
        self.session = session
        self.bot_id = bot_id

    def _direct_bot_filter(self, model):
        if self.bot_id is None or not hasattr(model, "bot_id"):
            return None
        return model.bot_id == self.bot_id

    async def dashboard(self, days: int | None) -> DashboardSnapshot:
        now = datetime.now(timezone.utc)
        start = None if days is None else now - timedelta(days=days)
        previous_start = None if start is None else start - timedelta(days=days)

        users = await self._comparison(User, User.created_at, start, previous_start)
        questions = await self._comparison(
            Question, Question.created_at, start, previous_start
        )
        answers = await self._comparison(Answer, Answer.created_at, start, previous_start)
        revenue = await self._payment_sum_comparison(start, previous_start)
        trials = await self._payment_count_comparison(
            start, previous_start, kinds=("trial", "initial", "binding")
        )
        rebills = await self._payment_count_comparison(
            start, previous_start, kinds=("rebill", "renewal", "recurring")
        )

        rebill_total = await self._payment_count(
            start, kinds=("rebill", "renewal", "recurring"), success_only=False
        )
        rebill_success = await self._payment_count(
            start, kinds=("rebill", "renewal", "recurring"), success_only=True
        )

        active_vip_filters = [
            Subscription.access_until.is_not(None),
            Subscription.access_until > now,
        ]
        if self.bot_id is not None:
            active_vip_filters.append(Subscription.bot_id == self.bot_id)
        active_vip = int(
            await self.session.scalar(
                select(func.count(Subscription.id)).where(
                    *active_vip_filters,
                )
            )
            or 0
        )
        active_card_filters = [
            PaymentMethod.is_active.is_(True),
            PaymentMethod.is_recurrent.is_(True),
            PaymentMethod.binding_id.is_not(None),
            PaymentMethod.blocked_at.is_(None),
        ]
        if self.bot_id is not None:
            active_card_filters.append(PaymentMethod.bot_id == self.bot_id)
        active_cards = int(
            await self.session.scalar(
                select(func.count(PaymentMethod.id)).where(*active_card_filters)
            )
            or 0
        )
        dead_users = await self._dead_users()
        arpu = round(revenue.current / users.current) if users.current else 0

        return DashboardSnapshot(
            users=users,
            questions=questions,
            answers=answers,
            revenue_kopecks=revenue,
            trials=trials,
            rebills=rebills,
            successful_rebill_rate=(
                round(rebill_success / rebill_total * 100, 1) if rebill_total else 0.0
            ),
            active_vip=active_vip,
            active_cards=active_cards,
            dead_users=dead_users,
            arpu_kopecks=arpu,
        )

    async def chart(self, days: int) -> list[ChartPoint]:
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
                or_(
                    *(DeliveryOutbox.last_error.ilike(p) for p in PERMANENT_ERRORS)
                ),
            )
            .group_by(DeliveryOutbox.chat_id)
            .subquery()
        )

        points: list[ChartPoint] = []
        for offset in range(days):
            left = start + timedelta(days=offset)
            right = left + timedelta(days=1)
            points.append(
                ChartPoint(
                    label=left.strftime("%d.%m"),
                    users=await self._count_between(User, User.created_at, left, right),
                    blocked=int(
                        await self.session.scalar(
                            select(func.count(first_failure.c.chat_id)).where(
                                first_failure.c.blocked_at >= left,
                                first_failure.c.blocked_at < right,
                            )
                        )
                        or 0
                    ),
                    questions=await self._count_between(
                        Question, Question.created_at, left, right
                    ),
                    answers=await self._count_between(
                        Answer, Answer.created_at, left, right
                    ),
                    revenue_kopecks=await self._payment_sum_between(left, right),
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
    ) -> tuple[list[UserRow], int]:
        now = datetime.now(timezone.utc)
        filters = []
        if self.bot_id is not None:
            filters.append(User.bot_id == self.bot_id)
        cleaned = query.strip().lstrip("@")
        if cleaned:
            if cleaned.isdigit():
                value = int(cleaned)
                filters.append(or_(User.id == value, User.telegram_id == value))
            else:
                pattern = f"%{cleaned}%"
                filters.append(
                    or_(
                        User.username.ilike(pattern),
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                    )
                )

        active_vip = exists(
            select(Subscription.id).where(
                Subscription.user_id == User.id,
                Subscription.access_until.is_not(None),
                Subscription.access_until > now,
            )
        )
        if vip == "active":
            filters.append(active_vip)
        elif vip == "inactive":
            filters.append(~active_vip)

        dead = exists(
            select(DeliveryOutbox.id).where(
                DeliveryOutbox.chat_id == User.telegram_id,
                DeliveryOutbox.status == "failed",
                or_(
                    *(DeliveryOutbox.last_error.ilike(p) for p in PERMANENT_ERRORS)
                ),
            )
        )
        if health == "alive":
            filters.append(~dead)
        elif health == "dead":
            filters.append(dead)

        if source_id is not None:
            filters.append(
                exists(
                    select(SourceAttribution.id).where(
                        SourceAttribution.user_id == User.id,
                        SourceAttribution.source_id == source_id,
                    )
                )
            )

        total = int(
            await self.session.scalar(select(func.count(User.id)).where(*filters))
            or 0
        )

        last_event = (
            select(
                CrmEvent.user_id.label("user_id"),
                func.max(CrmEvent.occurred_at).label("last_event_at"),
            )
            .group_by(CrmEvent.user_id)
            .subquery()
        )
        sent = (
            select(
                Question.sender_id.label("user_id"),
                func.count(Question.id).label("questions_sent"),
            )
            .group_by(Question.sender_id)
            .subquery()
        )
        answered = (
            select(
                Question.recipient_id.label("user_id"),
                func.count(Answer.id).label("answers_count"),
            )
            .join(Answer, Answer.question_id == Question.id)
            .group_by(Question.recipient_id)
            .subquery()
        )

        result = await self.session.execute(
            select(
                User.id,
                User.telegram_id,
                User.username,
                User.first_name,
                User.created_at,
                last_event.c.last_event_at,
                TrafficSource.name.label("source_name"),
                Subscription.access_until,
                func.coalesce(sent.c.questions_sent, 0).label("questions_sent"),
                func.coalesce(answered.c.answers_count, 0).label("answers_count"),
                dead.label("is_dead"),
            )
            .outerjoin(last_event, last_event.c.user_id == User.id)
            .outerjoin(sent, sent.c.user_id == User.id)
            .outerjoin(answered, answered.c.user_id == User.id)
            .outerjoin(Subscription, Subscription.user_id == User.id)
            .outerjoin(SourceAttribution, SourceAttribution.user_id == User.id)
            .outerjoin(TrafficSource, TrafficSource.id == SourceAttribution.source_id)
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
                last_event_at=row.last_event_at,
                source_name=row.source_name,
                vip_until=row.access_until,
                questions_sent=int(row.questions_sent or 0),
                answers_count=int(row.answers_count or 0),
                is_dead=bool(row.is_dead),
            )
            for row in result
        ]
        return rows, total

    async def sources(self) -> list[SourceRow]:
        now = datetime.now(timezone.utc)
        source_query = select(TrafficSource)
        if self.bot_id is not None:
            source_query = source_query.where(TrafficSource.bot_id == self.bot_id)
        result = await self.session.execute(
            source_query.order_by(TrafficSource.id.desc())
        )
        rows: list[SourceRow] = []

        for source in result.scalars():
            users = int(
                await self.session.scalar(
                    select(func.count(SourceAttribution.id)).where(
                        SourceAttribution.source_id == source.id
                    )
                )
                or 0
            )
            vip_users = int(
                await self.session.scalar(
                    select(func.count(func.distinct(SourceAttribution.user_id)))
                    .join(
                        Subscription,
                        Subscription.user_id == SourceAttribution.user_id,
                    )
                    .where(
                        SourceAttribution.source_id == source.id,
                        Subscription.access_until.is_not(None),
                        Subscription.access_until > now,
                    )
                )
                or 0
            )
            paid_users = int(
                await self.session.scalar(
                    select(
                        func.count(
                            func.distinct(Subscription.user_id)
                        )
                    )
                    .select_from(PaymentAttempt)
                    .join(
                        Subscription,
                        Subscription.id == PaymentAttempt.subscription_id,
                    )
                    .join(
                        SourceAttribution,
                        SourceAttribution.user_id == Subscription.user_id,
                    )
                    .where(
                        SourceAttribution.source_id == source.id,
                        PaymentAttempt.status.in_(SUCCESS_STATUSES),
                    )
                )
                or 0
            )
            payments = int(
                await self.session.scalar(
                    select(func.count(PaymentAttempt.id))
                    .select_from(PaymentAttempt)
                    .join(
                        Subscription,
                        Subscription.id == PaymentAttempt.subscription_id,
                    )
                    .join(
                        SourceAttribution,
                        SourceAttribution.user_id == Subscription.user_id,
                    )
                    .where(
                        SourceAttribution.source_id == source.id,
                        PaymentAttempt.status.in_(SUCCESS_STATUSES),
                    )
                )
                or 0
            )
            revenue = int(
                await self.session.scalar(
                    select(
                        func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)
                    )
                    .join(
                        Subscription,
                        Subscription.id == PaymentAttempt.subscription_id,
                    )
                    .join(
                        SourceAttribution,
                        SourceAttribution.user_id == Subscription.user_id,
                    )
                    .where(
                        SourceAttribution.source_id == source.id,
                        PaymentAttempt.status.in_(SUCCESS_STATUSES),
                    )
                )
                or 0
            )
            roi = (
                round((revenue - source.spend_kopecks) / source.spend_kopecks * 100, 1)
                if source.spend_kopecks
                else None
            )
            rows.append(
                SourceRow(
                    source=source,
                    users=users,
                    vip_users=vip_users,
                    paid_users=paid_users,
                    payments=payments,
                    revenue_kopecks=revenue,
                    cpa_kopecks=(
                        round(source.spend_kopecks / users)
                        if users else None
                    ),
                    vip_cpa_kopecks=(
                        round(source.spend_kopecks / vip_users)
                        if vip_users else None
                    ),
                    payment_cpa_kopecks=(
                        round(source.spend_kopecks / paid_users)
                        if paid_users else None
                    ),
                    registration_conversion_percent=(
                        round(users / source.clicks * 100, 1)
                        if source.clicks else None
                    ),
                    payment_conversion_percent=(
                        round(paid_users / users * 100, 1)
                        if users else None
                    ),
                    roi_percent=roi,
                )
            )
        return rows

    async def _comparison(self, model, column, start, previous_start):
        current = await self._count_since(model, column, start)
        previous = 0
        if start is not None and previous_start is not None:
            previous = await self._count_between(model, column, previous_start, start)
        return ComparisonMetric(current=current, previous=previous)

    async def _count_since(self, model, column, start):
        query = select(func.count(model.id))
        direct = self._direct_bot_filter(model)
        if direct is not None:
            query = query.where(direct)
        elif self.bot_id is not None and model is Question:
            query = query.join(User, User.id == Question.recipient_id).where(User.bot_id == self.bot_id)
        elif self.bot_id is not None and model is Answer:
            query = query.join(Question, Question.id == Answer.question_id).join(User, User.id == Question.recipient_id).where(User.bot_id == self.bot_id)
        if start is not None:
            query = query.where(column >= start)
        return int(await self.session.scalar(query) or 0)

    async def _count_between(self, model, column, left, right):
        query = select(func.count(model.id))
        direct = self._direct_bot_filter(model)
        if direct is not None:
            query = query.where(direct)
        elif self.bot_id is not None and model is Question:
            query = query.join(User, User.id == Question.recipient_id).where(User.bot_id == self.bot_id)
        elif self.bot_id is not None and model is Answer:
            query = query.join(Question, Question.id == Answer.question_id).join(User, User.id == Question.recipient_id).where(User.bot_id == self.bot_id)
        query = query.where(column >= left, column < right)
        return int(await self.session.scalar(query) or 0)

    async def _payment_sum_comparison(self, start, previous_start):
        current = await self._payment_sum_since(start)
        previous = (
            await self._payment_sum_between(previous_start, start)
            if start is not None and previous_start is not None
            else 0
        )
        return ComparisonMetric(current=current, previous=previous)

    async def _payment_count_comparison(self, start, previous_start, kinds):
        current = await self._payment_count(start, kinds=kinds, success_only=True)
        previous = 0
        if start is not None and previous_start is not None:
            previous = int(
                await self.session.scalar(
                    select(func.count(PaymentAttempt.id)).where(
                        PaymentAttempt.created_at >= previous_start,
                        PaymentAttempt.created_at < start,
                        PaymentAttempt.status.in_(SUCCESS_STATUSES),
                        PaymentAttempt.attempt_kind.in_(kinds),
                    )
                )
                or 0
            )
        return ComparisonMetric(current=current, previous=previous)

    async def _payment_count(self, start, kinds, success_only):
        filters = [PaymentAttempt.attempt_kind.in_(kinds)]
        if self.bot_id is not None:
            filters.append(PaymentAttempt.bot_id == self.bot_id)
        if start is not None:
            filters.append(PaymentAttempt.created_at >= start)
        if success_only:
            filters.append(PaymentAttempt.status.in_(SUCCESS_STATUSES))
        return int(
            await self.session.scalar(
                select(func.count(PaymentAttempt.id)).where(*filters)
            )
            or 0
        )

    async def _payment_sum_since(self, start):
        filters = [PaymentAttempt.status.in_(SUCCESS_STATUSES)]
        if self.bot_id is not None:
            filters.append(PaymentAttempt.bot_id == self.bot_id)
        if start is not None:
            filters.append(PaymentAttempt.created_at >= start)
        return int(
            await self.session.scalar(
                select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0))
                .where(*filters)
            )
            or 0
        )

    async def _payment_sum_between(self, left, right):
        return int(
            await self.session.scalar(
                select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0))
                .where(
                    PaymentAttempt.status.in_(SUCCESS_STATUSES),
                    PaymentAttempt.created_at >= left,
                    PaymentAttempt.created_at < right,
                    *([PaymentAttempt.bot_id == self.bot_id] if self.bot_id is not None else []),
                )
            )
            or 0
        )

    async def _dead_users(self):
        return int(
            await self.session.scalar(
                select(func.count(func.distinct(User.id)))
                .join(DeliveryOutbox, DeliveryOutbox.chat_id == User.telegram_id)
                .where(
                    DeliveryOutbox.status == "failed",
                    *([DeliveryOutbox.bot_id == self.bot_id] if self.bot_id is not None else []),
                    or_(
                        *(DeliveryOutbox.last_error.ilike(p) for p in PERMANENT_ERRORS)
                    ),
                )
            )
            or 0
        )
