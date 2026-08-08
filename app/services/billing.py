from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import PaymentAttempt, PaymentMethod, Subscription
from app.repositories.billing import BillingRepository
from app.services.impaya import ImpayaClient

INSUFFICIENT_FUNDS_CODES = {"AMOUNT_EXCEED", "INSUFFICIENT_FUNDS", "NOT_ENOUGH_FUNDS"}
BLOCKING_CODES = {"CARD_BLOCKED", "CARD_EXPIRED", "LOST_CARD", "STOLEN_CARD", "BINDING_INACTIVE", "PAYMENT_OPTION_DISABLED"}
SUCCESS_STATES = {"COMPLETED", "CONFIRMED", "PAID", "SUCCESS", "SUCCEEDED", "CHARGED"}
DUPLICATE_OPERATION_CODES = {"DUPLICATE_PROCESSING_ORDER_ID"}
ZERO_TRANSACTION_IDS = {"", "00000000-0000-0000-0000-000000000000"}
PRIMARY_ACCESS_KINDS = {"primary", "test_primary", "admin_primary"}
FALLBACK_ACCESS_KINDS = {"fallback", "test_fallback", "admin_fallback"}


class ChargeDecision(StrEnum):
    SUCCESS = "success"
    INSUFFICIENT = "insufficient"
    BLOCKED = "blocked"
    RETRY_LATER = "retry_later"
    PENDING = "pending"


@dataclass(slots=True)
class ChargeResult:
    decision: ChargeDecision
    attempt: PaymentAttempt
    access_until: datetime | None

    @property
    def successful(self) -> bool:
        return self.decision == ChargeDecision.SUCCESS


def _transaction_id(data: dict, current: str | None = None) -> str | None:
    transaction = data.get("transaction") or {}
    value = transaction.get("transaction_id") or data.get("transaction_id")
    if value is None:
        return current
    normalized = str(value).strip()
    if normalized in ZERO_TRANSACTION_IDS:
        return current
    return normalized


class BillingService:
    def __init__(
        self,
        session: AsyncSession,
        client: ImpayaClient,
        *,
        primary_amount: int = 29900,
        primary_duration: timedelta = timedelta(days=3),
        fallback_amount: int = 9900,
        fallback_duration: timedelta = timedelta(days=1),
        **_: object,
    ) -> None:
        self.session = session
        self.repo = BillingRepository(session)
        self.client = client
        self.primary_amount = primary_amount
        self.primary_duration = primary_duration
        self.fallback_amount = fallback_amount
        self.fallback_duration = fallback_duration

    def _period_for_attempt(self, attempt: PaymentAttempt) -> timedelta:
        return (
            self.primary_duration
            if attempt.attempt_kind in PRIMARY_ACCESS_KINDS
            else self.fallback_duration
        )

    async def renew(self, subscription: Subscription, method: PaymentMethod) -> ChargeResult:
        now = datetime.now(timezone.utc)
        pending = await self.repo.pending_recurrent_attempt(subscription.id)
        if pending is not None:
            return await self._recover_known_operation(
                subscription,
                pending,
                access_period=self._period_for_attempt(pending),
                now=now,
            )

        cycle = now.date().isoformat()
        primary = await self._charge(
            subscription,
            method,
            kind="primary",
            amount=self.primary_amount,
            access_period=self.primary_duration,
            cycle=cycle,
        )
        if primary.successful or primary.decision != ChargeDecision.INSUFFICIENT:
            return primary
        return await self._charge(
            subscription,
            method,
            kind="fallback",
            amount=self.fallback_amount,
            access_period=self.fallback_duration,
            cycle=cycle,
        )

    async def test_charge(
        self,
        subscription: Subscription,
        method: PaymentMethod,
        *,
        amount: int,
        access_period: timedelta,
        kind: str,
    ) -> ChargeResult:
        return await self._charge(
            subscription,
            method,
            kind=kind,
            amount=amount,
            access_period=access_period,
            cycle=f"test-{uuid.uuid4().hex[:20]}",
        )

    async def finalize_operation(
        self,
        customer_operation_id: str,
    ) -> tuple[bool, PaymentAttempt | None, bool]:
        attempt = await self.repo.attempt_by_operation_id(
            customer_operation_id,
            for_update=True,
        )
        if attempt is None:
            return False, None, False
        if attempt.status == "success":
            return True, attempt, False

        result = await self.client.state(
            customer_operation_id=customer_operation_id,
            recurrent=True,
        )
        attempt.raw_response = json.dumps(result.data, ensure_ascii=False)
        transaction = result.data.get("transaction") or {}
        state = str(transaction.get("state") or result.data.get("state") or "").upper()
        attempt.transaction_id = _transaction_id(result.data, attempt.transaction_id)

        if not result.success or state not in SUCCESS_STATES:
            attempt.error_code = result.error_code
            attempt.error_message = result.error_message
            await self.session.commit()
            return False, attempt, False

        subscription = await self.session.get(Subscription, attempt.subscription_id)
        if subscription is None:
            return False, attempt, False

        self._mark_success(
            subscription,
            attempt,
            self._period_for_attempt(attempt),
            datetime.now(timezone.utc),
        )
        await self.session.commit()
        return True, attempt, True

    async def _recover_known_operation(
        self,
        subscription: Subscription,
        attempt: PaymentAttempt,
        *,
        access_period: timedelta,
        now: datetime,
    ) -> ChargeResult:
        verification = await self.client.state(
            customer_operation_id=attempt.customer_operation_id,
            recurrent=True,
        )
        transaction = verification.data.get("transaction") or {}
        state = str(
            transaction.get("state")
            or verification.data.get("state")
            or ""
        ).upper()
        attempt.raw_response = json.dumps(
            {"state": verification.data},
            ensure_ascii=False,
        )
        attempt.transaction_id = _transaction_id(
            verification.data,
            attempt.transaction_id,
        )

        if verification.success and state in SUCCESS_STATES:
            self._mark_success(subscription, attempt, access_period, now)
            await self.session.commit()
            return ChargeResult(
                ChargeDecision.SUCCESS,
                attempt,
                subscription.access_until,
            )

        attempt.status = "pending"
        attempt.completed_at = None
        attempt.error_code = verification.error_code
        attempt.error_message = verification.error_message
        subscription.status = "payment_pending"
        subscription.next_charge_at = now + timedelta(minutes=30)
        await self.session.commit()
        return ChargeResult(
            ChargeDecision.PENDING,
            attempt,
            subscription.access_until,
        )

    async def _charge(
        self,
        subscription: Subscription,
        method: PaymentMethod,
        *,
        kind: str,
        amount: int,
        access_period: timedelta,
        cycle: str,
    ) -> ChargeResult:
        now = datetime.now(timezone.utc)
        existing = await self.repo.attempt(subscription.id, cycle, kind)
        if existing is not None:
            existing_code = (existing.error_code or "").upper()
            if (
                existing.status == "pending"
                or existing_code in DUPLICATE_OPERATION_CODES
            ):
                return await self._recover_known_operation(
                    subscription,
                    existing,
                    access_period=access_period,
                    now=now,
                )
            return ChargeResult(
                self._decision(existing),
                existing,
                subscription.access_until,
            )

        if not method.binding_id or not method.impaya_user_id:
            raise RuntimeError("Recurrent binding is incomplete")

        op = (
            f"{subscription.bot_id}_sub_{subscription.id}_"
            f"{cycle.replace('-', '')[:16]}_{kind}"
        )[:64]
        attempt = PaymentAttempt(
            bot_id=subscription.bot_id,
            subscription_id=subscription.id,
            customer_operation_id=op,
            billing_cycle_key=cycle,
            attempt_kind=kind,
            amount_kopecks=amount,
            status="pending",
        )
        self.session.add(attempt)
        await self.session.flush()

        result = await self.client.recurrent_pay(
            customer_operation_id=op,
            amount=amount,
            binding_id=method.binding_id,
            impaya_user_id=method.impaya_user_id,
            merchant_user_id=method.merchant_user_id,
        )
        attempt.raw_response = json.dumps(result.data, ensure_ascii=False)
        attempt.transaction_id = _transaction_id(result.data, attempt.transaction_id)

        if result.success:
            return await self._recover_known_operation(
                subscription,
                attempt,
                access_period=access_period,
                now=now,
            )

        code = (result.error_code or "").upper()
        attempt.error_code = result.error_code
        attempt.error_message = result.error_message

        if code in DUPLICATE_OPERATION_CODES:
            return await self._recover_known_operation(
                subscription,
                attempt,
                access_period=access_period,
                now=now,
            )

        attempt.completed_at = now

        if code in INSUFFICIENT_FUNDS_CODES:
            attempt.status = "insufficient_funds"
            subscription.status = "past_due"
            self._tomorrow(subscription, now)
            decision = ChargeDecision.INSUFFICIENT
        elif code in BLOCKING_CODES:
            attempt.status = "failed"
            method.is_active = False
            method.blocked_at = now
            subscription.auto_renew = False
            subscription.status = "payment_method_blocked"
            subscription.next_charge_at = None
            decision = ChargeDecision.BLOCKED
        elif (
            result.status_code is None
            or (result.status_code and result.status_code >= 500)
            or code
            in {
                "HTTP_CLIENT_ERROR",
                "TIMEOUT",
                "PENDING",
                "TRANSACTION_NOT_FOUND",
            }
        ):
            attempt.status = "pending"
            subscription.status = "payment_pending"
            subscription.next_charge_at = now + timedelta(minutes=30)
            decision = ChargeDecision.PENDING
        else:
            attempt.status = "failed"
            subscription.status = "past_due"
            self._tomorrow(subscription, now)
            decision = ChargeDecision.RETRY_LATER

        await self.session.commit()
        return ChargeResult(decision, attempt, subscription.access_until)

    def _mark_success(
        self,
        subscription: Subscription,
        attempt: PaymentAttempt,
        period: timedelta,
        now: datetime,
    ) -> None:
        explicitly_cancelled = (
            subscription.auto_renew is False
            and subscription.cancelled_at is not None
        )
        base = max(subscription.access_until or now, now)
        subscription.access_until = base + period
        subscription.last_successful_plan = attempt.attempt_kind

        if explicitly_cancelled:
            subscription.auto_renew = False
            subscription.next_charge_at = None
            subscription.status = "cancelled_active"
        else:
            subscription.next_charge_at = subscription.access_until
            subscription.status = (
                "active_3_days"
                if attempt.attempt_kind in PRIMARY_ACCESS_KINDS
                else "active_1_day"
            )
            subscription.auto_renew = True
            subscription.cancelled_at = None

        attempt.status = "success"
        attempt.completed_at = now
        attempt.error_code = None
        attempt.error_message = None

    @staticmethod
    def _tomorrow(subscription: Subscription, now: datetime) -> None:
        subscription.next_charge_at = now + timedelta(days=1)

    @staticmethod
    def _decision(attempt: PaymentAttempt) -> ChargeDecision:
        return {
            "success": ChargeDecision.SUCCESS,
            "insufficient_funds": ChargeDecision.INSUFFICIENT,
            "pending": ChargeDecision.PENDING,
        }.get(attempt.status, ChargeDecision.RETRY_LATER)
