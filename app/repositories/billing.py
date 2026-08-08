from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.billing import PaymentAttempt, PaymentMethod, Subscription


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def subscription_for_user(self, user_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.bot_id == require_current_bot().id,
                Subscription.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_subscription(self, user_id: int) -> Subscription:
        item = await self.subscription_for_user(user_id)
        if item:
            return item
        item = Subscription(bot_id=require_current_bot().id, user_id=user_id)
        self.session.add(item)
        await self.session.flush()
        return item

    async def payment_method_for_user(self, user_id: int) -> PaymentMethod | None:
        result = await self.session.execute(
            select(PaymentMethod).where(
                PaymentMethod.bot_id == require_current_bot().id,
                PaymentMethod.user_id == user_id,
            )
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
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars())

    async def due_subscription_ids(
        self,
        now: datetime,
        *,
        limit: int = 100,
    ) -> list[int]:
        result = await self.session.execute(
            select(Subscription.id)
            .where(
                Subscription.auto_renew.is_(True),
                Subscription.next_charge_at.is_not(None),
                Subscription.next_charge_at <= now,
                Subscription.status.not_in(
                    (
                        "cancelled",
                        "cancelled_active",
                        "expired",
                        "payment_method_blocked",
                    )
                ),
            )
            .order_by(Subscription.next_charge_at, Subscription.id)
            .limit(limit)
        )
        return list(result.scalars())

    async def try_subscription_lock(self, subscription_id: int) -> bool:
        bind = self.session.get_bind()
        if bind.dialect.name != "postgresql":
            return True
        value = await self.session.scalar(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": int(subscription_id)},
        )
        return bool(value)

    async def release_subscription_lock(self, subscription_id: int) -> None:
        bind = self.session.get_bind()
        if bind.dialect.name != "postgresql":
            return
        await self.session.execute(
            text("SELECT pg_advisory_unlock(:key)"),
            {"key": int(subscription_id)},
        )

    async def lock_subscription_transaction(self, subscription_id: int) -> None:
        """Serialize user/admin mutations with the recurrent-charge worker.

        The worker owns a session advisory lock while an external charge is in
        flight. Mutations use the transaction-scoped variant of the same key so
        they either win before charging starts or wait for the in-flight charge
        to finish. The xact lock is released automatically on commit/rollback.
        """
        bind = self.session.get_bind()
        if bind.dialect.name != "postgresql":
            return
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int(subscription_id)},
        )

    async def expire_finished_access(self, now: datetime) -> int:
        result = await self.session.execute(
            update(Subscription)
            .where(
                Subscription.auto_renew.is_(False),
                Subscription.access_until.is_not(None),
                Subscription.access_until <= now,
                Subscription.status.in_(("cancelled_active", "past_due")),
            )
            .values(status="expired", next_charge_at=None)
        )
        await self.session.commit()
        return int(result.rowcount or 0)

    async def attempt(
        self, subscription_id: int, cycle: str, kind: str
    ) -> PaymentAttempt | None:
        result = await self.session.execute(
            select(PaymentAttempt).where(
                PaymentAttempt.bot_id == require_current_bot().id,
                PaymentAttempt.subscription_id == subscription_id,
                PaymentAttempt.billing_cycle_key == cycle,
                PaymentAttempt.attempt_kind == kind,
            )
        )
        return result.scalar_one_or_none()

    async def pending_recurrent_attempt(
        self,
        subscription_id: int,
    ) -> PaymentAttempt | None:
        """Return unresolved recurrent work before creating another charge.

        This deliberately ignores the calendar billing-cycle key. A payment can
        become pending shortly before midnight and still be the same external
        operation after the date changes; issuing a new operation at that point
        could charge the customer twice.
        """
        result = await self.session.execute(
            select(PaymentAttempt)
            .where(
                PaymentAttempt.bot_id == require_current_bot().id,
                PaymentAttempt.subscription_id == subscription_id,
                PaymentAttempt.status == "pending",
                PaymentAttempt.attempt_kind.in_(("primary", "fallback")),
            )
            .order_by(PaymentAttempt.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def cancel_auto_renew(
        self,
        subscription: Subscription,
        *,
        cancelled_at: datetime,
    ) -> Subscription:
        await self.lock_subscription_transaction(subscription.id)
        # The object may have been loaded before we waited for an in-flight
        # recurrent charge. Refresh it so cancellation always applies to the
        # authoritative post-charge state instead of overwriting stale values.
        await self.session.refresh(subscription)
        subscription.auto_renew = False
        subscription.next_charge_at = None
        subscription.cancelled_at = cancelled_at
        subscription.status = (
            "cancelled_active"
            if subscription.access_until is not None
            and subscription.access_until > cancelled_at
            else "expired"
        )
        await self.session.flush()
        return subscription

    async def attempt_by_operation_id(
        self,
        customer_operation_id: str,
        *,
        for_update: bool = False,
    ) -> PaymentAttempt | None:
        statement = select(PaymentAttempt).where(
            PaymentAttempt.bot_id == require_current_bot().id,
            PaymentAttempt.customer_operation_id == customer_operation_id,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
