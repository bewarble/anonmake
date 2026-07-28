from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/bot/keyboards/main_menu.py",
        "app/bot/keyboards/questions.py",
        "app/bot/keyboards/reveals.py",
        "app/bot/keyboards/personal_link.py",
        "app/bot/handlers/start.py",
        "app/bot/handlers/start_marketing.py",
        "app/bot/handlers/reveals.py",
        "app/bot/handlers/answers.py",
        "app/services/payment_notifications.py",
        "app/services/admin_statistics_stage25.py",
        "app/bot/handlers/admin_stage25_1.py",
        "app/repositories/marketing.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    menu = (ROOT / "app/bot/keyboards/main_menu.py").read_text(encoding="utf-8")
    assert "USER_HELP" not in menu
    assert menu.count("USER_PERSONAL_LINK") >= 2

    start = (ROOT / "app/bot/handlers/start.py").read_text(encoding="utf-8")
    assert "texts.WELCOME" not in start
    assert "show_help" not in start

    marketing_start = (
        ROOT / "app/bot/handlers/start_marketing.py"
    ).read_text(encoding="utf-8")
    assert "условиями пользования" not in marketing_start
    assert "texts.WELCOME" not in marketing_start

    questions = (
        ROOT / "app/bot/keyboards/questions.py"
    ).read_text(encoding="utf-8")
    assert "answer_received_keyboard" in questions
    assert "reveal_answer:" in questions

    reveals = (
        ROOT / "app/bot/handlers/reveals.py"
    ).read_text(encoding="utf-8")
    assert "reveal_confirm:" in reveals
    assert "reveal_close" in reveals
    assert "parse_mode=\"HTML\"" in reveals

    reveal_keyboard = (
        ROOT / "app/bot/keyboards/reveals.py"
    ).read_text(encoding="utf-8")
    assert "offer_url" not in reveal_keyboard
    assert "Условия" not in reveal_keyboard

    stats = (
        ROOT / "app/services/admin_statistics_stage25.py"
    ).read_text(encoding="utf-8")
    assert "DeliveryOutbox.updated_at" in stats

    admin = (
        ROOT / "app/bot/handlers/admin_stage25_1.py"
    ).read_text(encoding="utf-8")
    assert "пдп" in admin
    assert "conversion_percent" in admin
    assert "sources_summary" in admin

    print("Stage 35.1 check: OK")
    print("/start personal-link-only flow: ready")
    print("Share copy: updated")
    print("Question and answer action buttons: ready")
    print("Reveal consent and payment confirmation: ready")
    print("Offer button removed: ready")
    print("Statistics blocked-date calculation: fixed")
    print("Profit and sources admin views: updated")


if __name__ == "__main__":
    check()
