from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import PaymentAttempt, PaymentMethod, Subscription
from app.repositories.billing import BillingRepository
from app.services.impaya import ImpayaClient, ImpayaResult

BLOCKING_CODES = {
    "CARD_BLOCKED",
    "CARD_EXPIRED",
    "LOST_CARD",
    "STOLEN_CARD",
    "BINDING_INACTIVE",
    "PAYMENT_OPTION_DISABLED",
}


class BillingService:
    def __init__(
        self,
        session: AsyncSession,
        client: ImpayaClient,
        *,
        trial_amount: int = 100,
        primary_amount: int = 29900,
        fallback_amount: int = 9900,
    ) -> None:
        self.session = session
        self.repo = BillingRepository(session)
        self.client = client
        self.trial_amount = trial_amount
        self.primary_amount = primary_amount
        self.fallback_amount = fallback_amount

    async def create_binding(
        self,
        *,
        user_id: int,
        success_url: str,
        fail_url: str,
    ) -> str:
        subscription = await self.repo.get_or_create_subscription(user_id)
        method = await self.repo.payment_method_for_user(user_id)
        if method is None:
            method = PaymentMethod(
                user_id=user_id,
                merchant_user_id=f"anonmake_{user_id}",
            )
            self.session.add(method)
            await self.session.flush()

        operation_id = f"bind_{user_id}_{uuid.uuid4().hex[:20]}"
        result = await self.client.bind_init(
            customer_operation_id=operation_id,
            merchant_user_id=method.merchant_user_id,
            success_url=success_url,
            fail_url=fail_url,
        )
        if not result.success or not result.data.get("form_url"):
            raise RuntimeError(result.error_message or "Impaya bind-init failed")

        method.impaya_operation_id = result.data.get("impaya_operation_id")
        subscription.status = "pending_binding"
        await self.session.commit()
        return str(result.data["form_url"])

    async def charge_trial(
        self, subscription: Subscription, method: PaymentMethod
    ) -> bool:
        return await self._charge(
            subscription, method, "trial", self.trial_amount, timedelta(hours=24)
        )

    async def renew(self, subscription: Subscription, method: PaymentMethod) -> bool:
        if await self._charge(
            subscription, method, "primary", self.primary_amount, timedelta(days=3)
        ):
            return True
        return await self._charge(
            subscription, method, "fallback", self.fallback_amount, timedelta(days=1)
        )

    async def cancel(self, subscription: Subscription) -> None:
        subscription.auto_renew = False
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.now(timezone.utc)
        subscription.next_charge_at = None
        await self.session.commit()

    async def _charge(
        self,
        subscription: Subscription,
        method: PaymentMethod,
        kind: str,
        amount: int,
        access_period: timedelta,
    ) -> bool:
        now = datetime.now(timezone.utc)
        cycle = now.date().isoformat()
        existing = await self.repo.attempt(subscription.id, cycle, kind)
        if existing is not None:
            return existing.status == "success"

        operation_id = f"sub_{subscription.id}_{cycle.replace('-', '')}_{kind}"
        attempt = PaymentAttempt(
            subscription_id=subscription.id,
            customer_operation_id=operation_id,
            billing_cycle_key=cycle,
            attempt_kind=kind,
            amount_kopecks=amount,
        )
        self.session.add(attempt)
        await self.session.flush()

        result = await self.client.recurrent_pay(
            customer_operation_id=operation_id,
            amount=amount,
            binding_id=method.binding_id or "",
            impaya_user_id=method.impaya_user_id or "",
            merchant_user_id=method.merchant_user_id,
        )
        attempt.raw_response = json.dumps(result.data, ensure_ascii=False)
        attempt.transaction_id = result.data.get("transaction_id")
        attempt.completed_at = now

        if result.success:
            attempt.status = "success"
            base = max(subscription.access_until or now, now)
            subscription.access_until = base + access_period
            subscription.next_charge_at = subscription.access_until
            subscription.status = (
                "trial_active" if kind == "trial"
                else "active_3_days" if kind == "primary"
                else "active_1_day"
            )
            subscription.last_successful_plan = kind
            await self.session.commit()
            return True

        attempt.status = "failed"
        attempt.error_code = result.error_code
        attempt.error_message = result.error_message
        subscription.status = "past_due"
        if result.error_code in BLOCKING_CODES:
            method.is_active = False
            method.blocked_at = now
            subscription.auto_renew = False
            subscription.status = "payment_method_blocked"
            subscription.next_charge_at = None
        else:
            tomorrow = (now + timedelta(days=1)).date()
            subscription.next_charge_at = datetime.combine(
                tomorrow, datetime.min.time(), tzinfo=timezone.utc
            )
        await self.session.commit()
        return False
