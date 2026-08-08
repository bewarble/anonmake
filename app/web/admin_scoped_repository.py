from __future__ import annotations

from sqlalchemy import func, or_, select

from app.models import Answer, Question, User
from app.models.billing import PaymentAttempt, PaymentMethod, Subscription
from app.models.crm import CrmEvent
from app.models.delivery import DeliveryOutbox
from app.models.marketing import SourceAttribution, TrafficSource
from app.models.reveal import RevealCheckout
from app.web.admin_repository import (
    PERMANENT_DELIVERY_ERRORS,
    SUCCESS_PAYMENT_STATUSES,
    SourceRow,
    UserDetails,
    UserRow,
    WebAdminRepository,
)


class ScopedWebAdminRepository(WebAdminRepository):
    """Project-aware view of the legacy web-admin repository.

    ``bot_id=None`` intentionally means the super-admin "all projects" scope.
    Any concrete bot id is enforced in every project-owned query below.
    """

    def __init__(self, session, *, bot_id: int | None) -> None:
        super().__init__(session)
        self.bot_id = bot_id

    async def users(self, *, query: str, page: int, page_size: int):
        if self.bot_id is None:
            return await super().users(query=query, page=page, page_size=page_size)

        filters = [User.bot_id == self.bot_id]
        cleaned = query.strip().lstrip("@")
        if cleaned:
            if cleaned.isdigit():
                numeric = int(cleaned)
                numeric_filters = [User.telegram_id == numeric]
                if -(2**31) <= numeric <= (2**31 - 1):
                    numeric_filters.append(User.id == numeric)
                filters.append(or_(*numeric_filters))
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
            await self.session.scalar(select(func.count(User.id)).where(*filters))
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
                (Subscription.user_id == User.id)
                & (Subscription.bot_id == self.bot_id),
            )
            .outerjoin(SourceAttribution, SourceAttribution.user_id == User.id)
            .outerjoin(
                TrafficSource,
                (TrafficSource.id == SourceAttribution.source_id)
                & (TrafficSource.bot_id == self.bot_id),
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
        if self.bot_id is None:
            return await super().user_details(user_id)

        user = await self.session.scalar(
            select(User).where(User.id == user_id, User.bot_id == self.bot_id)
        )
        if user is None:
            return None

        subscription = await self.session.scalar(
            select(Subscription).where(
                Subscription.bot_id == self.bot_id,
                Subscription.user_id == user.id,
            )
        )
        payment_method = await self.session.scalar(
            select(PaymentMethod).where(
                PaymentMethod.bot_id == self.bot_id,
                PaymentMethod.user_id == user.id,
            )
        )
        source = await self.session.scalar(
            select(TrafficSource)
            .join(SourceAttribution, SourceAttribution.source_id == TrafficSource.id)
            .where(
                TrafficSource.bot_id == self.bot_id,
                SourceAttribution.user_id == user.id,
            )
        )

        sent_questions = await self._count(Question, Question.sender_id == user.id)
        received_questions = await self._count(Question, Question.recipient_id == user.id)
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
                select(func.count(PaymentAttempt.id)).where(
                    PaymentAttempt.bot_id == self.bot_id,
                    PaymentAttempt.subscription_id == (
                        subscription.id if subscription else -1
                    ),
                    PaymentAttempt.status.in_(SUCCESS_PAYMENT_STATUSES),
                )
            )
            or 0
        )
        revenue_kopecks = int(
            await self.session.scalar(
                select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)).where(
                    PaymentAttempt.bot_id == self.bot_id,
                    PaymentAttempt.subscription_id == (
                        subscription.id if subscription else -1
                    ),
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
        answers_count = int(
            await self.session.scalar(
                select(func.count(Answer.id))
                .join(Question, Question.id == Answer.question_id)
                .where(
                    or_(
                        Question.sender_id == user.id,
                        Question.recipient_id == user.id,
                    )
                )
            )
            or 0
        )
        reveal_clicks_count = int(
            await self.session.scalar(
                select(func.count(CrmEvent.id)).where(
                    CrmEvent.user_id == user.id,
                    CrmEvent.event_type.ilike("%reveal%"),
                )
            )
            or 0
        )
        last_delivery = await self.session.scalar(
            select(DeliveryOutbox)
            .where(
                DeliveryOutbox.bot_id == self.bot_id,
                DeliveryOutbox.chat_id == user.telegram_id,
            )
            .order_by(DeliveryOutbox.updated_at.desc())
            .limit(1)
        )
        is_bot_blocked = bool(
            last_delivery
            and last_delivery.status == "failed"
            and last_delivery.last_error
            and "blocked" in last_delivery.last_error.lower()
        )
        last_activity_at = await self.session.scalar(
            select(func.max(CrmEvent.occurred_at)).where(CrmEvent.user_id == user.id)
        )
        last_successful_payment = await self.session.scalar(
            select(PaymentAttempt)
            .where(
                PaymentAttempt.bot_id == self.bot_id,
                PaymentAttempt.subscription_id == (subscription.id if subscription else -1),
                PaymentAttempt.status == "success",
            )
            .order_by(PaymentAttempt.id.desc())
            .limit(1)
        )
        last_failed_payment = await self.session.scalar(
            select(PaymentAttempt)
            .where(
                PaymentAttempt.bot_id == self.bot_id,
                PaymentAttempt.subscription_id == (subscription.id if subscription else -1),
                PaymentAttempt.status.in_(("failed", "insufficient_funds", "pending")),
            )
            .order_by(PaymentAttempt.id.desc())
            .limit(1)
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
            last_successful_payment=last_successful_payment,
            last_failed_payment=last_failed_payment,
            sent_questions_count=sent_questions,
            received_questions_count=received_questions,
            answers_count=answers_count,
            reveal_clicks_count=reveal_clicks_count,
            is_bot_blocked=is_bot_blocked,
            last_activity_at=last_activity_at,
        )

    async def payments(self, *, page: int, page_size: int, query: str = "", status: str = "", kind: str = ""):
        if self.bot_id is None:
            return await super().payments(
                page=page, page_size=page_size, query=query, status=status, kind=kind
            )

        filters = [PaymentAttempt.bot_id == self.bot_id]
        cleaned = query.strip().lstrip("@")
        if cleaned:
            pattern = f"%{cleaned}%"
            if cleaned.isdigit():
                numeric = int(cleaned)
                numeric_filters = [User.telegram_id == numeric]
                if -(2**31) <= numeric <= (2**31 - 1):
                    numeric_filters.extend((User.id == numeric, PaymentAttempt.id == numeric))
                filters.append(or_(*numeric_filters))
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

        base = (
            select(PaymentAttempt, Subscription, User, PaymentMethod)
            .join(
                Subscription,
                (PaymentAttempt.subscription_id == Subscription.id)
                & (Subscription.bot_id == self.bot_id),
            )
            .join(
                User,
                (Subscription.user_id == User.id) & (User.bot_id == self.bot_id),
            )
            .outerjoin(
                PaymentMethod,
                (PaymentMethod.user_id == User.id)
                & (PaymentMethod.bot_id == self.bot_id),
            )
            .where(*filters)
        )
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.subquery())
            )
            or 0
        )
        result = await self.session.execute(
            base.order_by(PaymentAttempt.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        return result.all(), total

    async def payment_details(self, attempt_id: int):
        if self.bot_id is None:
            return await super().payment_details(attempt_id)
        result = await self.session.execute(
            select(PaymentAttempt, Subscription, User, PaymentMethod)
            .join(
                Subscription,
                (PaymentAttempt.subscription_id == Subscription.id)
                & (Subscription.bot_id == self.bot_id),
            )
            .join(
                User,
                (Subscription.user_id == User.id) & (User.bot_id == self.bot_id),
            )
            .outerjoin(
                PaymentMethod,
                (PaymentMethod.user_id == User.id)
                & (PaymentMethod.bot_id == self.bot_id),
            )
            .where(
                PaymentAttempt.id == attempt_id,
                PaymentAttempt.bot_id == self.bot_id,
            )
        )
        return result.one_or_none()

    async def sources(self) -> list[SourceRow]:
        if self.bot_id is None:
            return await super().sources()
        users_count = func.count(SourceAttribution.id).label("users_count")
        result = await self.session.execute(
            select(TrafficSource, users_count)
            .outerjoin(SourceAttribution, SourceAttribution.source_id == TrafficSource.id)
            .where(TrafficSource.bot_id == self.bot_id)
            .group_by(TrafficSource.id)
            .order_by(TrafficSource.id.desc())
        )
        rows: list[SourceRow] = []
        for source, count in result.all():
            count = int(count or 0)
            rows.append(
                SourceRow(
                    source=source,
                    users_count=count,
                    cpa_kopecks=(round(source.spend_kopecks / count) if count else None),
                )
            )
        return rows

    async def delivery(self, *, page: int, page_size: int):
        if self.bot_id is None:
            return await super().delivery(page=page, page_size=page_size)
        total = int(
            await self.session.scalar(
                select(func.count(DeliveryOutbox.id)).where(
                    DeliveryOutbox.bot_id == self.bot_id
                )
            )
            or 0
        )
        result = await self.session.execute(
            select(DeliveryOutbox)
            .where(DeliveryOutbox.bot_id == self.bot_id)
            .order_by(DeliveryOutbox.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), total
