from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_python_syntax() -> int:
    count = 0
    for path in sorted((ROOT / "app").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count += 1
    return count


def check_router_registry() -> None:
    text = (ROOT / "app/bot/handlers/__init__.py").read_text(encoding="utf-8")
    required = (
        "admin_router",
        "admin_marketing_router",
        "source_management_router",
        "start_marketing_router",
        "start_router",
        "questions_router",
        "reveals_router",
        "answers_router",
        "errors_router",
    )
    for name in required:
        assert f"include_router({name})" in text, name

    forbidden = (
        "admin_stage25_router",
        "admin_reply_router",
        "admin_bi_router",
        "admin_minimal_router",
        "admin_control_router",
    )
    for name in forbidden:
        assert f"include_router({name})" not in text, name


def check_no_artifacts() -> None:
    assert not list(ROOT.glob("anonmake-stage-*.zip"))


def check_current_admin() -> None:
    handler = (ROOT / "app/bot/handlers/admin_stage25_1.py").read_text(encoding="utf-8")
    assert 'F.text == "Статистика"' in handler
    assert 'F.text == "Прибыль"' in handler
    assert 'F.text == "Выгрузка"' in handler
    assert 'F.text == "Рефералы"' in handler
    assert 'F.text == "Рассылка"' in handler
    assert r'^adminm:source:\d+$' in handler


def main() -> None:
    count = check_python_syntax()
    check_router_registry()
    check_no_artifacts()
    check_current_admin()
    print("Project check: OK")
    print(f"Python files parsed: {count}")
    print("Router registry: clean")
    print("Legacy artifacts: removed")
    print("Current admin surface: verified")


if __name__ == "__main__":
    main()
