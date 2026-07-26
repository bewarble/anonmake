from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import PaymentAttempt, PaymentMethod, Subscription


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def subscription_for_user(self, user_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_subscription(self, user_id: int) -> Subscription:
        item = await self.subscription_for_user(user_id)
        if item:
            return item
        item = Subscription(user_id=user_id)
        self.session.add(item)
        await self.session.flush()
        return item

    async def payment_method_for_user(self, user_id: int) -> PaymentMethod | None:
        result = await self.session.execute(
            select(PaymentMethod).where(PaymentMethod.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def due_subscriptions(self, now: datetime, limit: int = 100) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(
                Subscription.auto_renew.is_(True),
                Subscription.next_charge_at.is_not(None),
                Subscription.next_charge_at <= now,
                Subscription.status.not_in(("cancelled", "payment_method_blocked")),
            )
            .order_by(Subscription.next_charge_at)
            .limit(limit)
        )
        return list(result.scalars())

    async def attempt(
        self, subscription_id: int, cycle: str, kind: str
    ) -> PaymentAttempt | None:
        result = await self.session.execute(
            select(PaymentAttempt).where(
                PaymentAttempt.subscription_id == subscription_id,
                PaymentAttempt.billing_cycle_key == cycle,
                PaymentAttempt.attempt_kind == kind,
            )
        )
        return result.scalar_one_or_none()
