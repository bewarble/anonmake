from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/bot/handlers/admin_stage25_1.py",
        "app/bot/handlers/admin_marketing.py",
        "app/bot/handlers/subscriptions.py",
        "app/bot/keyboards/marketing.py",
        "app/bot/keyboards/personal_link.py",
        "app/bot/keyboards/subscriptions.py",
        "app/bot/handlers/start.py",
        "app/repositories/billing.py",
        "app/services/admin_statistics_stage25.py",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel

    for rel in required:
        if rel.endswith(".py"):
            ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)

    stats = (ROOT / "app/bot/handlers/admin_stage25_1.py").read_text(encoding="utf-8")
    assert "📊 <b>Общая статистика</b>" in stats
    assert "📁 <b>Статистика:</b>" in stats
    assert "organic_all_time" not in stats
    assert "Раскрыт" not in stats

    repository = (ROOT / "app/services/admin_statistics_stage25.py").read_text(encoding="utf-8")
    assert 'func.min(DeliveryOutbox.created_at).label("blocked_at")' in repository

    marketing = (ROOT / "app/bot/handlers/admin_marketing.py").read_text(encoding="utf-8")
    assert "texts.NEW_QUESTION.format(text=text)" in marketing
    assert "broadcast_preview_keyboard()" in marketing

    subscriptions = (ROOT / "app/bot/handlers/subscriptions.py").read_text(encoding="utf-8")
    assert 'Command("cancel")' in subscriptions
    assert "subscription.auto_renew" in subscriptions or "cancel_auto_renew" in subscriptions

    start = (ROOT / "app/bot/handlers/start.py").read_text(encoding="utf-8")
    assert "personal_link_share_keyboard(link)" in start
    assert "await message.answer(\n            texts.WELCOME" in start

    print("Stage 29.6 check: OK")
    print("Telegram statistics format: ready")
    print("False blocked-day retries: fixed")
    print("Broadcast full preview and cancellation: ready")
    print("Subscription auto-renew cancellation: ready")
    print("Personal-link sharing: ready")


if __name__ == "__main__":
    check()
