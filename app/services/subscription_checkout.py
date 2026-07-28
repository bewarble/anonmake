from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.billing import PaymentAttempt, PaymentMethod, Subscription
from app.repositories.billing import BillingRepository
from app.services.impaya import ImpayaClient

SUCCESS_STATES = {
    "COMPLETED",
    "CONFIRMED",
    "PAID",
    "SUCCESS",
    "SUCCEEDED",
    "VOIDED",
}


class SubscriptionCheckoutService:
    def __init__(
        self,
        session: AsyncSession,
        client: ImpayaClient,
        *,
        payment_form_url_template: str,
        trial_amount: int = 100,
        trial_duration: timedelta = timedelta(hours=24),
    ) -> None:
        self.session = session
        self.client = client
        self.payment_form_url_template = payment_form_url_template
        self.trial_amount = trial_amount
        self.trial_duration = trial_duration
        self.repo = BillingRepository(session)

    async def create_test_invoice(
        self,
        *,
        user_id: int,
        public_base_url: str,
    ) -> tuple[str, str]:
        subscription = await self.repo.get_or_create_subscription(user_id)
        method = await self.repo.payment_method_for_user(user_id)
        if method is None:
            current_bot = require_current_bot()
            method = PaymentMethod(
                bot_id=current_bot.id,
                user_id=user_id,
                merchant_user_id=f"{current_bot.code}_anonmake_{user_id}",
            )
            self.session.add(method)
            await self.session.flush()

        current_bot = require_current_bot()
        operation_id = f"{current_bot.code}_test_{user_id}_{uuid.uuid4().hex[:16]}"[:64]
        attempt = PaymentAttempt(
            bot_id=current_bot.id,
            subscription_id=subscription.id,
            customer_operation_id=operation_id,
            billing_cycle_key=f"test-{uuid.uuid4().hex[:16]}",
            attempt_kind="trial",
            amount_kopecks=self.trial_amount,
            status="pending",
        )
        self.session.add(attempt)
        await self.session.flush()

        public_base = public_base_url.rstrip("/")
        result = await self.client.create_trial_invoice(
            customer_operation_id=operation_id,
            amount=self.trial_amount,
            merchant_user_id=method.merchant_user_id,
            success_url=(
                f"{public_base}/payments/subscription/success/{operation_id}"
            ),
            fail_url=(
                f"{public_base}/payments/subscription/fail/{operation_id}"
            ),
        )

        attempt.raw_response = json.dumps(result.data, ensure_ascii=False)
        attempt.transaction_id = result.data.get("transaction_id")
        invoice_id = result.data.get("invoice_id")

        if not result.success or not invoice_id:
            attempt.status = "failed"
            attempt.error_code = result.error_code
            attempt.error_message = result.error_message
            attempt.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
            raise RuntimeError(
                result.error_message or "Impaya did not return invoice_id"
            )

        await self.session.commit()
        return (
            self.payment_form_url_template.format(invoice_id=invoice_id),
            operation_id,
        )

    async def finalize(
        self,
        operation_id: str,
    ) -> tuple[bool, PaymentAttempt | None]:
        attempt = await self.repo.attempt_by_operation_id(
            operation_id,
            for_update=True,
        )
        if attempt is None:
            return False, None, False

        # Повторный return/webhook не должен повторно начислять доступ
        # и отправлять Telegram-уведомление.
        if attempt.status == "success":
            return True, attempt, False

        result = await self.client.state(
            customer_operation_id=operation_id
        )
        transaction = result.data.get("transaction") or {}
        state = str(
            transaction.get("state")
            or result.data.get("state")
            or ""
        ).upper()

        attempt.raw_response = json.dumps(result.data, ensure_ascii=False)
        attempt.transaction_id = (
            transaction.get("transaction_id")
            or result.data.get("transaction_id")
            or attempt.transaction_id
        )

        binding = result.data.get("binding") or {}
        binding_id = binding.get("binding_id")
        impaya_user_id = binding.get("user_id")
        binding_created = binding.get("created") is True

        payment_confirmed = (
            result.success
            and state in SUCCESS_STATES
            and binding_created
            and bool(binding_id)
            and bool(impaya_user_id)
        )

        if not payment_confirmed:
            attempt.error_code = result.error_code
            attempt.error_message = result.error_message
            await self.session.commit()
            return False, attempt, False

        reported_amount = (
            transaction.get("amount")
            or result.data.get("amount")
        )
        if (
            reported_amount is not None
            and int(reported_amount) != attempt.amount_kopecks
        ):
            attempt.status = "failed"
            attempt.error_code = "AMOUNT_MISMATCH"
            attempt.error_message = (
                f"Expected {attempt.amount_kopecks}, got {reported_amount}"
            )
            attempt.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
            return False, attempt, False

        subscription = await self.session.get(
            Subscription,
            attempt.subscription_id,
        )
        if subscription is None:
            return False, attempt, False

        method = await self.repo.payment_method_for_user(
            subscription.user_id
        )
        binding = result.data.get("binding") or {}
        payment_option = result.data.get("payment_option") or {}
        card = payment_option.get("card") or {}

        if method is None:
            method = PaymentMethod(
                user_id=subscription.user_id,
                merchant_user_id=(
                    binding.get("merchant_user_id")
                    or f"anonmake_{subscription.user_id}"
                ),
            )
            self.session.add(method)

        binding_id = binding.get("binding_id") or binding.get("id")
        impaya_user_id = (
            binding.get("user_id")
            or binding.get("impaya_user_id")
        )
        if not binding_id or not impaya_user_id:
            attempt.error_code = "BINDING_NOT_RETURNED"
            attempt.error_message = (
                "Successful payment has no recurrent binding"
            )
            await self.session.commit()
            return False, attempt, False

        method.binding_id = str(binding_id)
        method.impaya_user_id = str(impaya_user_id)
        method.merchant_user_id = (
            binding.get("merchant_user_id")
            or method.merchant_user_id
        )
        method.masked_pan = (
            card.get("masked_pan")
            or card.get("pan_mask")
            or method.masked_pan
        )
        method.card_brand = card.get("brand") or method.card_brand
        method.is_active = True
        method.is_recurrent = True
        method.blocked_at = None

        now = datetime.now(timezone.utc)
        access_base = max(subscription.access_until or now, now)
        subscription.access_until = access_base + self.trial_duration
        subscription.next_charge_at = subscription.access_until
        subscription.status = "trial_active"
        subscription.auto_renew = True
        subscription.cancelled_at = None
        subscription.last_successful_plan = "trial"

        attempt.status = "success"
        attempt.completed_at = now
        attempt.error_code = None
        attempt.error_message = None

        await self.session.commit()
        # Только этот вызов впервые перевёл попытку в success.
        return True, attempt, True
