from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Question, User
from app.models.billing import PaymentAttempt, PaymentMethod, Subscription
from app.models.crm import CrmEvent
from app.models.delivery import DeliveryOutbox
from app.models.marketing import Broadcast, SourceAttribution, TrafficSource

SUCCESS_STATUSES = ("success", "paid", "completed")


@dataclass(slots=True, frozen=True)
class Funnel:
    users: int
    question_senders: int
    answerers: int
    vip_users: int
    active_cards: int


@dataclass(slots=True, frozen=True)
class PeriodMetric:
    label: str
    users: int
    questions: int
    answers: int
    revenue_kopecks: int


@dataclass(slots=True, frozen=True)
class SourcePerformance:
    id: int
    name: str
    spend_kopecks: int
    users: int
    vip_users: int
    cpa_kopecks: int | None
    vip_cpa_kopecks: int | None


@dataclass(slots=True, frozen=True)
class OperationsSummary:
    delivery_pending: int
    delivery_failed: int
    broadcasts_active: int
    crm_events_24h: int


class WebAdminProRepository:
    def __init__(self, session: AsyncSession, bot_id: int | None = None) -> None:
        self.session = session
        self.bot_id = bot_id

    async def funnel(self) -> Funnel:
        now = datetime.now(timezone.utc)
        users = await self._count(User)

        sender_query = select(func.count(func.distinct(Question.sender_id))).join(
            User, User.id == Question.sender_id
        )
        answerer_query = (
            select(func.count(func.distinct(Question.recipient_id)))
            .join(Answer, Answer.question_id == Question.id)
            .join(User, User.id == Question.recipient_id)
        )
        if self.bot_id is not None:
            sender_query = sender_query.where(User.bot_id == self.bot_id)
            answerer_query = answerer_query.where(User.bot_id == self.bot_id)
        question_senders = int(await self.session.scalar(sender_query) or 0)
        answerers = int(await self.session.scalar(answerer_query) or 0)

        vip_filters = [
            Subscription.access_until.is_not(None),
            Subscription.access_until > now,
        ]
        card_filters = [
            PaymentMethod.is_active.is_(True),
            PaymentMethod.is_recurrent.is_(True),
            PaymentMethod.binding_id.is_not(None),
            PaymentMethod.blocked_at.is_(None),
        ]
        if self.bot_id is not None:
            vip_filters.append(Subscription.bot_id == self.bot_id)
            card_filters.append(PaymentMethod.bot_id == self.bot_id)
        vip_users = int(
            await self.session.scalar(
                select(func.count(Subscription.id)).where(*vip_filters)
            )
            or 0
        )
        active_cards = int(
            await self.session.scalar(
                select(func.count(PaymentMethod.id)).where(*card_filters)
            )
            or 0
        )

        return Funnel(
            users=users,
            question_senders=question_senders,
            answerers=answerers,
            vip_users=vip_users,
            active_cards=active_cards,
        )

    async def periods(self, days: int = 14) -> list[PeriodMetric]:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days - 1)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        rows: list[PeriodMetric] = []

        for offset in range(days):
            left = start + timedelta(days=offset)
            right = left + timedelta(days=1)

            users = await self._count_between(User, User.created_at, left, right)
            questions = await self._count_between(
                Question,
                Question.created_at,
                left,
                right,
            )
            answers = await self._count_between(
                Answer,
                Answer.created_at,
                left,
                right,
            )
            revenue_filters = [
                PaymentAttempt.status.in_(SUCCESS_STATUSES),
                PaymentAttempt.created_at >= left,
                PaymentAttempt.created_at < right,
            ]
            if self.bot_id is not None:
                revenue_filters.append(PaymentAttempt.bot_id == self.bot_id)
            revenue = int(
                await self.session.scalar(
                    select(
                        func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)
                    ).where(*revenue_filters)
                )
                or 0
            )
            rows.append(
                PeriodMetric(
                    label=left.strftime("%d.%m"),
                    users=users,
                    questions=questions,
                    answers=answers,
                    revenue_kopecks=revenue,
                )
            )
        return rows

    async def source_performance(self, limit: int = 12) -> list[SourcePerformance]:
        now = datetime.now(timezone.utc)

        users_count = func.count(
            func.distinct(SourceAttribution.user_id)
        ).label("users_count")

        source_query = (
            select(TrafficSource, users_count)
            .outerjoin(
                SourceAttribution,
                SourceAttribution.source_id == TrafficSource.id,
            )
            .group_by(TrafficSource.id)
            .order_by(users_count.desc(), TrafficSource.id.desc())
            .limit(limit)
        )
        if self.bot_id is not None:
            source_query = source_query.where(TrafficSource.bot_id == self.bot_id)
        result = await self.session.execute(source_query)

        rows: list[SourcePerformance] = []
        for source, users in result.all():
            users = int(users or 0)
            vip_users = int(
                await self.session.scalar(
                    select(func.count(func.distinct(SourceAttribution.user_id)))
                    .join(
                        Subscription,
                        (Subscription.user_id == SourceAttribution.user_id)
                        & (Subscription.bot_id == source.bot_id),
                    )
                    .where(
                        SourceAttribution.source_id == source.id,
                        Subscription.access_until.is_not(None),
                        Subscription.access_until > now,
                    )
                )
                or 0
            )

            rows.append(
                SourcePerformance(
                    id=source.id,
                    name=source.name,
                    spend_kopecks=source.spend_kopecks,
                    users=users,
                    vip_users=vip_users,
                    cpa_kopecks=(
                        round(source.spend_kopecks / users)
                        if users
                        else None
                    ),
                    vip_cpa_kopecks=(
                        round(source.spend_kopecks / vip_users)
                        if vip_users
                        else None
                    ),
                )
            )

        return rows

    async def operations(self) -> OperationsSummary:
        day = datetime.now(timezone.utc) - timedelta(days=1)

        return OperationsSummary(
            delivery_pending=await self._count(
                DeliveryOutbox,
                DeliveryOutbox.status.in_(("pending", "processing")),
            ),
            delivery_failed=await self._count(
                DeliveryOutbox,
                DeliveryOutbox.status == "failed",
            ),
            broadcasts_active=await self._count(
                Broadcast,
                Broadcast.status.in_(("queued", "processing")),
            ),
            crm_events_24h=await self._count(
                CrmEvent,
                CrmEvent.occurred_at >= day,
            ),
        )

    async def _count(self, model, *conditions) -> int:
        query = select(func.count(model.id)).where(*conditions)
        if self.bot_id is not None:
            if hasattr(model, "bot_id"):
                query = query.where(model.bot_id == self.bot_id)
            elif model is CrmEvent:
                query = query.join(User, User.id == CrmEvent.user_id).where(
                    User.bot_id == self.bot_id
                )
        return int(await self.session.scalar(query) or 0)

    async def _count_between(
        self,
        model,
        column,
        left: datetime,
        right: datetime,
    ) -> int:
        query = select(func.count(model.id)).where(
            column >= left,
            column < right,
        )
        if self.bot_id is not None:
            if hasattr(model, "bot_id"):
                query = query.where(model.bot_id == self.bot_id)
            elif model is Question:
                query = query.join(User, User.id == Question.recipient_id).where(
                    User.bot_id == self.bot_id
                )
            elif model is Answer:
                query = (
                    query.join(Question, Question.id == Answer.question_id)
                    .join(User, User.id == Question.recipient_id)
                    .where(User.bot_id == self.bot_id)
                )
        return int(await self.session.scalar(query) or 0)
