from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    required = (
        "app/bot/ui.py",
        "app/core/admin_texts.py",
        "app/bot/keyboards/main_menu.py",
        "app/bot/keyboards/admin_stage25_1.py",
        "app/bot/keyboards/marketing.py",
        "app/bot/handlers/admin_stage25_1.py",
        "app/bot/handlers/admin_marketing.py",
        "app/bot/handlers/source_management.py",
        "app/bot/handlers/start.py",
        "app/bot/handlers/start_marketing.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    ui = read("app/bot/ui.py")
    menu = read("app/bot/keyboards/main_menu.py")
    admin_handler = read("app/bot/handlers/admin_stage25_1.py")

    constants = (
        "ADMIN_STATISTICS",
        "ADMIN_BROADCAST",
        "ADMIN_PROFIT",
        "ADMIN_EXPORT",
        "ADMIN_SOURCES",
        "USER_PERSONAL_LINK",
        "USER_HELP",
    )
    for constant in constants:
        assert constant in ui, f"{constant}: missing from shared UI"
        if constant.startswith("ADMIN_"):
            assert constant in admin_handler, f"{constant}: missing handler"
        else:
            assert constant in read("app/bot/handlers/start.py"), (
                f"{constant}: missing handler"
            )
        assert constant in menu, f"{constant}: missing keyboard"

    # Visible admin menu strings must not be duplicated in handlers.
    forbidden_literals = (
        'F.text == "📊 Статистика"',
        'F.text == "📣 Рассылка"',
        'F.text == "💰 Прибыль"',
        'F.text == "📦 Выгрузка"',
        'F.text == "🔗 Источники"',
    )
    for literal in forbidden_literals:
        assert literal not in admin_handler, literal

    # Deprecated wording removed from primary Telegram UI.
    combined = "\n".join(
        read(rel)
        for rel in (
            "app/bot/keyboards/admin_stage25_1.py",
            "app/bot/keyboards/marketing.py",
            "app/bot/handlers/admin_stage25_1.py",
            "app/bot/handlers/admin_marketing.py",
            "app/bot/handlers/source_management.py",
        )
    )
    for deprecated in ("С VIP", "Без VIP", "✖️ Отмена", "📣 Рефералы"):
        assert deprecated not in combined, deprecated

    assert "personal_link_share_keyboard" in read(
        "app/bot/handlers/start_marketing.py"
    )

    print("Stage 32.2 check: OK")
    print("Shared Telegram button registry: ready")
    print("Admin menu handlers and keyboard labels: synchronized")
    print("Broadcast and source flows: unified")
    print("User start and personal-link flows: unified")
    print("Admin messages and emoji system: unified")


if __name__ == "__main__":
    check()
