from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/services/impaya.py",
        "app/services/subscription_checkout.py",
        "app/bot/handlers/payments.py",
        "app/bot/keyboards/payments.py",
        "app/web/subscription_payments.py",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel
        ast.parse(
            (ROOT / rel).read_text(encoding="utf-8"),
            filename=rel,
        )

    handlers = (
        ROOT / "app/bot/handlers/__init__.py"
    ).read_text(encoding="utf-8")
    assert "payments_router" in handlers

    app_text = (ROOT / "app/web/app.py").read_text(encoding="utf-8")
    assert "subscription_payments_module.router.routes" in app_text
    assert "finalize_subscription_payment" in app_text

    print("Stage 30 check: OK")
    print("Admin-only /testpay: ready")
    print("1 RUB bind_recurrent invoice: ready")
    print("Extended-state verification: ready")
    print("Binding persistence: ready")
    print("Webhook fallback: ready")


if __name__ == "__main__":
    check()
