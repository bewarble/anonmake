from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "migrations/versions/20260728_0012_multibot_billing.py",
        "app/models/billing.py",
        "app/models/marketing.py",
        "app/repositories/billing.py",
        "app/services/subscription_checkout.py",
        "app/services/billing.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    billing = (ROOT / "app/models/billing.py").read_text(encoding="utf-8")
    assert billing.count("bot_id: Mapped[int]") >= 3
    assert "uq_payment_methods_bot_user" in billing
    assert "uq_subscriptions_bot_user" in billing
    assert "uq_payment_attempt_bot_operation" in billing

    marketing = (ROOT / "app/models/marketing.py").read_text(encoding="utf-8")
    assert "uq_traffic_sources_bot_code" in marketing

    checkout = (
        ROOT / "app/services/subscription_checkout.py"
    ).read_text(encoding="utf-8")
    assert "current_bot.code" in checkout
    assert "bot_id=current_bot.id" in checkout

    recurring = (ROOT / "app/services/billing.py").read_text(encoding="utf-8")
    assert "bot_id=subscription.bot_id" in recurring
    assert 'f"{subscription.bot_id}_sub_' in recurring

    print("Stage 38.3 check: OK")
    print("VIP subscriptions per bot: ready")
    print("Payment methods per bot: ready")
    print("Payment attempts per bot: ready")
    print("Traffic sources per bot: ready")
    print("Bot-prefixed payment operation IDs: ready")
    print("Four production bots: still disabled until compose rollout")


if __name__ == "__main__":
    check()
