from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.billing import BillingService, ChargeDecision
from app.services.impaya import ImpayaResult


class FakeRepo:
    async def attempt(self, subscription_id: int, cycle: str, kind: str):
        return None


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class ScenarioImpaya:
    def __init__(self, *, fallback_success: bool, primary_code: str = "AMOUNT_EXCEED") -> None:
        self.fallback_success = fallback_success
        self.primary_code = primary_code
        self.calls: list[int] = []

    async def recurrent_pay(
        self,
        *,
        customer_operation_id: str,
        amount: int,
        binding_id: str,
        impaya_user_id: str,
        merchant_user_id: str,
    ) -> ImpayaResult:
        self.calls.append(amount)

        if amount == 29900:
            return ImpayaResult(
                False,
                {
                    "success": False,
                    "error_code": self.primary_code,
                    "error_message": "simulated primary result",
                },
                200,
            )

        if amount == 9900 and self.fallback_success:
            return ImpayaResult(
                True,
                {
                    "success": True,
                    "transaction_id": "fallback-pay-result",
                },
                200,
            )

        if amount == 9900:
            return ImpayaResult(
                False,
                {
                    "success": False,
                    "error_code": "AMOUNT_EXCEED",
                    "error_message": "simulated fallback insufficient funds",
                },
                200,
            )

        raise AssertionError(f"Unexpected recurrent amount: {amount}")

    async def state(
        self,
        *,
        customer_operation_id: str,
        recurrent: bool = False,
    ) -> ImpayaResult:
        assert recurrent is True
        return ImpayaResult(
            True,
            {
                "success": True,
                "transaction": {
                    "customer_operation_id": customer_operation_id,
                    "transaction_id": "fallback-confirmed-transaction",
                    "state": "Completed",
                },
            },
            200,
        )


def subscription():
    return SimpleNamespace(
        id=9001,
        bot_id=2,
        user_id=7001,
        access_until=datetime.now(timezone.utc) + timedelta(hours=12),
        next_charge_at=datetime.now(timezone.utc),
        status="trial_active",
        last_successful_plan="trial",
        auto_renew=True,
        cancelled_at=None,
    )


def payment_method():
    return SimpleNamespace(
        binding_id="binding-test",
        impaya_user_id="impaya-user-test",
        merchant_user_id="merchant-user-test",
        is_active=True,
        is_recurrent=True,
        blocked_at=None,
    )


def service(client: ScenarioImpaya) -> BillingService:
    fake_session = FakeSession()
    billing = BillingService(
        fake_session,
        client,
        primary_amount=29900,
        primary_duration=timedelta(days=3),
        fallback_amount=9900,
        fallback_duration=timedelta(days=1),
    )
    billing.repo = FakeRepo()
    return billing


async def check_fallback_success() -> None:
    client = ScenarioImpaya(fallback_success=True)
    sub = subscription()
    before = sub.access_until

    result = await service(client).renew(sub, payment_method())

    assert client.calls == [29900, 9900], client.calls
    assert result.decision == ChargeDecision.SUCCESS
    assert result.attempt.attempt_kind == "fallback"
    assert result.attempt.amount_kopecks == 9900
    assert result.attempt.status == "success"
    assert result.attempt.transaction_id == "fallback-confirmed-transaction"
    assert sub.status == "active_1_day"
    assert sub.last_successful_plan == "fallback"
    assert sub.auto_renew is True
    assert sub.access_until >= before + timedelta(days=1)
    assert sub.next_charge_at == sub.access_until


async def check_double_insufficient() -> None:
    client = ScenarioImpaya(fallback_success=False)
    sub = subscription()
    started = datetime.now(timezone.utc)

    result = await service(client).renew(sub, payment_method())

    assert client.calls == [29900, 9900], client.calls
    assert result.decision == ChargeDecision.INSUFFICIENT
    assert result.attempt.attempt_kind == "fallback"
    assert result.attempt.amount_kopecks == 9900
    assert result.attempt.status == "insufficient_funds"
    assert result.attempt.error_code == "AMOUNT_EXCEED"
    assert sub.status == "past_due"
    assert sub.auto_renew is True
    assert sub.last_successful_plan == "trial"
    assert sub.next_charge_at >= started + timedelta(hours=23, minutes=59)


async def check_non_insufficient_does_not_fallback() -> None:
    client = ScenarioImpaya(
        fallback_success=False,
        primary_code="FRAUD_ERROR",
    )
    sub = subscription()

    result = await service(client).renew(sub, payment_method())

    assert client.calls == [29900], client.calls
    assert result.decision == ChargeDecision.RETRY_LATER
    assert result.attempt.attempt_kind == "primary"
    assert result.attempt.status == "failed"
    assert result.attempt.error_code == "FRAUD_ERROR"
    assert sub.status == "past_due"


async def main_async() -> None:
    await check_fallback_success()
    await check_double_insufficient()
    await check_non_insufficient_does_not_fallback()


def main() -> None:
    asyncio.run(main_async())
    print("Billing fallback behavior check: OK")
    print("299 -> insufficient -> 99 success: verified")
    print("299 -> insufficient -> 99 insufficient: verified")
    print("Non-insufficient primary failure does not trigger fallback: verified")


if __name__ == "__main__":
    main()
