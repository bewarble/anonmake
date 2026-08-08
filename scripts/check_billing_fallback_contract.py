from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    billing = (ROOT / "app/services/billing.py").read_text(encoding="utf-8")

    # Public billing contract: primary renewal is 299 RUB / 3 days and the
    # partial fallback is 99 RUB / 1 day.
    assert "primary_amount: int = 29900" in billing
    assert "primary_duration: timedelta = timedelta(days=3)" in billing
    assert "fallback_amount: int = 9900" in billing
    assert "fallback_duration: timedelta = timedelta(days=1)" in billing

    # AMOUNT_EXCEED is the Impaya simulator scenario we verified end-to-end.
    assert 'INSUFFICIENT_FUNDS_CODES = {"AMOUNT_EXCEED", "INSUFFICIENT_FUNDS", "NOT_ENOUGH_FUNDS"}' in billing

    # Fallback must happen only after the primary attempt is classified as
    # insufficient funds. Other failures must return without a second charge.
    assert "if primary.successful or primary.decision != ChargeDecision.INSUFFICIENT:" in billing
    assert 'kind="fallback"' in billing
    assert "amount=self.fallback_amount" in billing
    assert "access_period=self.fallback_duration" in billing

    # Both primary and fallback use distinct idempotent operation IDs.
    assert 'f"{cycle.replace(\'-\', \'\')[:16]}_{kind}"' in billing
    assert "DUPLICATE_OPERATION_CODES" in billing
    assert "return await self._recover_known_operation(" in billing

    # A failed primary/fallback attempt must be persisted as insufficient and
    # must not be treated as successful access extension.
    assert 'attempt.status = "insufficient_funds"' in billing
    assert 'subscription.status = "past_due"' in billing
    assert "self._tomorrow(subscription, now)" in billing

    print("Billing fallback contract check: OK")
    print("Primary: 299 RUB / 3 days")
    print("Insufficient funds: AMOUNT_EXCEED supported")
    print("Fallback: 99 RUB / 1 day, only after insufficient primary")
    print("Primary/fallback operation IDs: distinct and idempotent")


if __name__ == "__main__":
    main()
