from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.billing import PaymentAttempt, PaymentMethod
from app.models.reveal import RevealCheckout
from app.repositories.billing import BillingRepository
from app.services.impaya import ImpayaClient

logger = logging.getLogger(__name__)

SUCCESS_STATES = {
    "COMPLETED",
    "CONFIRMED",
    "PAID",
    "SUCCESS",
    "SUCCEEDED",
}


class RevealCheckoutService:
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
        self.billing = BillingRepository(session)

    def payment_url(self, invoice_id: str) -> str:
        if not self.payment_form_url_template:
            raise RuntimeError("IMPAYA_PAYMENT_FORM_URL_TEMPLATE is not configured")
        return self.payment_form_url_template.format(invoice_id=invoice_id)

    async def create(
        self,
        checkout: RevealCheckout,
        *,
        user_id: int,
        success_url: str,
        fail_url: str,
    ) -> str:
        if checkout.status == "completed":
            raise RuntimeError("Reveal checkout is already completed")
        # Double taps on the consent button must reuse the same pending invoice
        # instead of creating multiple payment intents for one reveal.
        if checkout.status == "payment_pending" and checkout.invoice_id:
            return self.payment_url(checkout.invoice_id)

        current_bot = require_current_bot()
        subscription = await self.billing.get_or_create_subscription(user_id)
        method = await self.billing.payment_method_for_user(user_id)

        if method is None:
            method = PaymentMethod(
                bot_id=current_bot.id,
                user_id=user_id,
                merchant_user_id=f"{current_bot.code}_anonmake_{user_id}",
            )
            self.session.add(method)
            await self.session.flush()

        operation_id = checkout.customer_operation_id
        if operation_id is None:
            operation_id = (
                f"{current_bot.code}_vip_"
                f"{checkout.id}_{uuid.uuid4().hex[:16]}"
            )[:64]

        result = await self.client.create_trial_invoice(
            customer_operation_id=operation_id,
            merchant_user_id=method.merchant_user_id,
            success_url=success_url,
            fail_url=fail_url,
            amount=self.trial_amount,
        )
        invoice_id = result.data.get("invoice_id")
        if not result.success or not invoice_id:
            raise RuntimeError(
                result.error_message or "Impaya did not return invoice_id"
            )

        checkout.customer_operation_id = operation_id
        checkout.invoice_id = str(invoice_id)
        checkout.transaction_id = result.data.get("transaction_id")
        checkout.status = "payment_pending"

        cycle_key = f"vip-trial-{checkout.id}"
        existing = await self.billing.attempt(
            subscription.id,
            cycle_key,
            "trial",
        )
        if existing is None:
            self.session.add(
                PaymentAttempt(
                    bot_id=current_bot.id,
                    subscription_id=subscription.id,
                    customer_operation_id=operation_id,
                    transaction_id=result.data.get("transaction_id"),
                    billing_cycle_key=cycle_key,
                    attempt_kind="trial",
                    amount_kopecks=self.trial_amount,
                    status="pending",
                )
            )

        await self.session.commit()
        return self.payment_url(str(invoice_id))

    async def finalize(
        self,
        checkout: RevealCheckout,
        *,
        user_id: int,
    ) -> bool:
        if checkout.status == "completed":
            return True
        if checkout.customer_operation_id is None:
            return False

        current_bot = require_current_bot()
        result = await self.client.state(
            customer_operation_id=checkout.customer_operation_id
        )
        transaction = result.data.get("transaction") or {}
        state = str(
            transaction.get("state")
            or result.data.get("state")
            or ""
        ).upper()
        binding = result.data.get("binding") or {}

        logger.info(
            "Impaya reveal checkout state",
            extra={
                "bot_code": current_bot.code,
                "checkout_id": checkout.id,
                "customer_operation_id": checkout.customer_operation_id,
                "impaya_http_status": result.status_code,
                "impaya_success": result.success,
                "impaya_state": state or "<empty>",
                "impaya_error_code": result.error_code or "",
                "impaya_has_binding": bool(
                    binding.get("binding_id") or binding.get("id")
                ),
            },
        )

        if not result.success or state not in SUCCESS_STATES:
            return False

        subscription = await self.billing.get_or_create_subscription(user_id)
        method = await self.billing.payment_method_for_user(user_id)
        payment_option = result.data.get("payment_option") or {}
        card = payment_option.get("card") or {}

        if method is None:
            method = PaymentMethod(
                bot_id=current_bot.id,
                user_id=user_id,
                merchant_user_id=(
                    binding.get("merchant_user_id")
                    or f"{current_bot.code}_anonmake_{user_id}"
                ),
            )
            self.session.add(method)

        method.binding_id = (
            binding.get("binding_id")
            or binding.get("id")
            or method.binding_id
        )
        method.impaya_user_id = (
            binding.get("user_id")
            or binding.get("impaya_user_id")
            or method.impaya_user_id
        )
        method.masked_pan = (
            card.get("masked_pan")
            or card.get("pan_mask")
            or method.masked_pan
        )
        method.card_brand = card.get("brand") or method.card_brand
        method.is_active = bool(method.binding_id)
        method.is_recurrent = bool(method.binding_id)

        now = datetime.now(timezone.utc)
        subscription.status = "trial_active"
        subscription.auto_renew = True
        access_base = max(subscription.access_until or now, now)
        subscription.access_until = access_base + self.trial_duration
        subscription.next_charge_at = subscription.access_until
        subscription.last_successful_plan = "trial"

        checkout.status = "completed"
        checkout.completed_at = now
        checkout.transaction_id = (
            transaction.get("transaction_id")
            or result.data.get("transaction_id")
            or checkout.transaction_id
        )

        attempt = await self.billing.attempt(
            subscription.id,
            f"vip-trial-{checkout.id}",
            "trial",
        )
        if attempt is not None:
            attempt.status = "success"
            attempt.completed_at = now
            attempt.transaction_id = checkout.transaction_id

        await self.session.commit()
        return True
