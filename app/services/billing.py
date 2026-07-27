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

class BillingService:
    def __init__(self, session: AsyncSession, client: ImpayaClient, *, primary_amount: int = 29900, primary_duration: timedelta = timedelta(days=3), fallback_amount: int = 9900, fallback_duration: timedelta = timedelta(days=1), **_: object) -> None:
        self.session=session; self.repo=BillingRepository(session); self.client=client
        self.primary_amount=primary_amount; self.primary_duration=primary_duration
        self.fallback_amount=fallback_amount; self.fallback_duration=fallback_duration

    async def renew(self, subscription: Subscription, method: PaymentMethod) -> ChargeResult:
        cycle=datetime.now(timezone.utc).date().isoformat()
        primary=await self._charge(subscription, method, kind="primary", amount=self.primary_amount, access_period=self.primary_duration, cycle=cycle)
        if primary.successful or primary.decision != ChargeDecision.INSUFFICIENT:
            return primary
        return await self._charge(subscription, method, kind="fallback", amount=self.fallback_amount, access_period=self.fallback_duration, cycle=cycle)

    async def test_charge(self, subscription: Subscription, method: PaymentMethod, *, amount: int, access_period: timedelta, kind: str) -> ChargeResult:
        return await self._charge(subscription, method, kind=kind, amount=amount, access_period=access_period, cycle=f"test-{uuid.uuid4().hex[:20]}")

    async def finalize_operation(self, customer_operation_id: str) -> tuple[bool, PaymentAttempt | None, bool]:
        attempt=await self.repo.attempt_by_operation_id(customer_operation_id, for_update=True)
        if attempt is None: return False, None, False
        if attempt.status == "success": return True, attempt, False
        result=await self.client.state(customer_operation_id=customer_operation_id)
        attempt.raw_response=json.dumps(result.data, ensure_ascii=False)
        transaction=result.data.get("transaction") or {}
        state=str(transaction.get("state") or result.data.get("state") or "").upper()
        attempt.transaction_id=transaction.get("transaction_id") or result.data.get("transaction_id") or attempt.transaction_id
        if not result.success or state not in SUCCESS_STATES:
            attempt.error_code=result.error_code; attempt.error_message=result.error_message
            await self.session.commit(); return False, attempt, False
        subscription=await self.session.get(Subscription, attempt.subscription_id)
        if subscription is None: return False, attempt, False
        period=self.primary_duration if attempt.attempt_kind in {"primary","test_primary"} else self.fallback_duration
        self._mark_success(subscription, attempt, period, datetime.now(timezone.utc))
        await self.session.commit(); return True, attempt, True

    async def _charge(self, subscription: Subscription, method: PaymentMethod, *, kind: str, amount: int, access_period: timedelta, cycle: str) -> ChargeResult:
        now=datetime.now(timezone.utc)
        existing=await self.repo.attempt(subscription.id, cycle, kind)
        if existing is not None:
            return ChargeResult(self._decision(existing), existing, subscription.access_until)
        if not method.binding_id or not method.impaya_user_id: raise RuntimeError("Recurrent binding is incomplete")
        op=f"sub_{subscription.id}_{cycle.replace('-','')[:20]}_{kind}"[:64]
        attempt=PaymentAttempt(subscription_id=subscription.id, customer_operation_id=op, billing_cycle_key=cycle, attempt_kind=kind, amount_kopecks=amount, status="pending")
        self.session.add(attempt); await self.session.flush()
        result=await self.client.recurrent_pay(customer_operation_id=op, amount=amount, binding_id=method.binding_id, impaya_user_id=method.impaya_user_id, merchant_user_id=method.merchant_user_id)
        attempt.raw_response=json.dumps(result.data, ensure_ascii=False); attempt.transaction_id=result.data.get("transaction_id")
        if result.success:
            self._mark_success(subscription, attempt, access_period, now); await self.session.commit()
            return ChargeResult(ChargeDecision.SUCCESS, attempt, subscription.access_until)
        code=(result.error_code or "").upper(); attempt.error_code=result.error_code; attempt.error_message=result.error_message; attempt.completed_at=now
        if code in INSUFFICIENT_FUNDS_CODES:
            attempt.status="insufficient_funds"; subscription.status="past_due"; self._tomorrow(subscription, now); decision=ChargeDecision.INSUFFICIENT
        elif code in BLOCKING_CODES:
            attempt.status="failed"; method.is_active=False; method.blocked_at=now; subscription.auto_renew=False; subscription.status="payment_method_blocked"; subscription.next_charge_at=None; decision=ChargeDecision.BLOCKED
        elif result.status_code is None or (result.status_code and result.status_code >= 500) or code in {"HTTP_CLIENT_ERROR","TIMEOUT","PENDING","TRANSACTION_NOT_FOUND"}:
            attempt.status="pending"; subscription.status="payment_pending"; subscription.next_charge_at=now+timedelta(minutes=30); decision=ChargeDecision.PENDING
        else:
            attempt.status="failed"; subscription.status="past_due"; self._tomorrow(subscription, now); decision=ChargeDecision.RETRY_LATER
        await self.session.commit(); return ChargeResult(decision, attempt, subscription.access_until)

    def _mark_success(self, subscription: Subscription, attempt: PaymentAttempt, period: timedelta, now: datetime) -> None:
        base=max(subscription.access_until or now, now); subscription.access_until=base+period; subscription.next_charge_at=subscription.access_until
        subscription.status="active_3_days" if attempt.attempt_kind in {"primary","test_primary"} else "active_1_day"
        subscription.last_successful_plan=attempt.attempt_kind; subscription.auto_renew=True; subscription.cancelled_at=None
        attempt.status="success"; attempt.completed_at=now; attempt.error_code=None; attempt.error_message=None

    @staticmethod
    def _tomorrow(
        subscription: Subscription,
        now: datetime,
    ) -> None:
        subscription.next_charge_at = now + timedelta(days=1)

    @staticmethod
    def _decision(attempt: PaymentAttempt) -> ChargeDecision:
        return {"success":ChargeDecision.SUCCESS,"insufficient_funds":ChargeDecision.INSUFFICIENT,"pending":ChargeDecision.PENDING}.get(attempt.status, ChargeDecision.RETRY_LATER)
