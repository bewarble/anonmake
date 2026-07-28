from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    targets = (
        ROOT / "app/core/texts.py",
        ROOT / "app/core/admin_texts.py",
        ROOT / "app/bot/ui.py",
        ROOT / "app/bot/handlers",
        ROOT / "app/bot/keyboards",
        ROOT / "app/web/templates",
        ROOT / "app/web/admin_ui.py",
    )

    forbidden = (
        "⭐ С доступом",
        "Без доступа",
        "⭐ Доступ",
        "Доступ открыт",
        "Доступ активен",
        "Доступ завершён",
        "<b>Рассылка</b>",
        "<b>Выгрузка</b>",
    )

    violations: list[str] = []
    for target in targets:
        paths = [target] if target.is_file() else target.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix not in {".py", ".html"}:
                continue
            source = path.read_text(encoding="utf-8")
            if path.suffix == ".py":
                ast.parse(source, filename=str(path))
            for phrase in forbidden:
                if phrase in source:
                    violations.append(f"{path.relative_to(ROOT)}: {phrase}")

    texts = (ROOT / "app/core/texts.py").read_text(encoding="utf-8")
    ui = (ROOT / "app/bot/ui.py").read_text(encoding="utf-8")
    assert "👑 VIP подписка" in texts
    assert "VIP статус активирован" in texts
    assert "1 ₽ — 1 день VIP статуса" in texts
    assert "👑 С VIP статусом" in ui
    assert "Без VIP статуса" in ui

    if violations:
        raise AssertionError("Stage 36 violations:\n- " + "\n- ".join(violations))

    print("Stage 36 check: OK")
    print("VIP subscription and VIP status terminology: unified")
    print("Telegram admin headings: plain and safe")
    print("Broadcast and export audiences: unified")
    print("Web admin terminology: unified")


if __name__ == "__main__":
    check()
