from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Question, User
from app.models.billing import PaymentAttempt, Subscription
from app.models.reveal import RevealCheckout


@dataclass(slots=True, frozen=True)
class AdminUserCard:
    user: User
    questions_sent: int
    questions_received: int
    answers_sent: int
    reveals: int
    successful_payments: int
    revenue_kopecks: int
    subscription: Subscription | None

    @property
    def vip_active(self) -> bool:
        if self.subscription is None or self.subscription.access_until is None:
            return False

        value = self.subscription.access_until
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value > datetime.now(timezone.utc)


class AdminUsersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def recent_users(
        self,
        *,
        page: int,
        page_size: int = 8,
    ) -> tuple[list[User], bool]:
        offset = max(page, 0) * page_size
        result = await self.session.execute(
            select(User)
            .order_by(User.id.desc())
            .offset(offset)
            .limit(page_size + 1)
        )
        items = list(result.scalars())
        has_next = len(items) > page_size
        return items[:page_size], has_next

    async def get_card(self, user_id: int) -> AdminUserCard | None:
        user = await self.session.get(User, user_id)
        if user is None:
            return None

        questions_sent = await self._count(
            Question,
            Question.sender_id == user.id,
        )
        questions_received = await self._count(
            Question,
            Question.recipient_id == user.id,
        )

        answers_sent = int(
            await self.session.scalar(
                select(func.count(Answer.id))
                .join(Question, Answer.question_id == Question.id)
                .where(Question.recipient_id == user.id)
            )
            or 0
        )

        reveals = int(
            await self.session.scalar(
                select(func.count(RevealCheckout.id)).where(
                    RevealCheckout.buyer_id == user.id,
                    RevealCheckout.status.in_(
                        ("paid", "completed", "success")
                    ),
                )
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
                    PaymentAttempt.status.in_(
                        ("success", "paid", "completed")
                    ),
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
                    PaymentAttempt.status.in_(
                        ("success", "paid", "completed")
                    ),
                )
            )
            or 0
        )

        subscription = await self.session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )

        return AdminUserCard(
            user=user,
            questions_sent=questions_sent,
            questions_received=questions_received,
            answers_sent=answers_sent,
            reveals=reveals,
            successful_payments=successful_payments,
            revenue_kopecks=revenue_kopecks,
            subscription=subscription,
        )

    async def _count(self, model, condition) -> int:
        value = await self.session.scalar(
            select(func.count(model.id)).where(condition)
        )
        return int(value or 0)
