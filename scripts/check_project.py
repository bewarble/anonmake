from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def python_files() -> list[Path]:
    return sorted((ROOT / "app").rglob("*.py")) + sorted(
        (ROOT / "scripts").rglob("*.py")
    )


def check_python_syntax() -> int:
    count = 0
    for path in python_files():
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count += 1
    return count


def check_local_imports() -> None:
    modules: set[str] = set()
    for path in python_files():
        relative = path.relative_to(ROOT).with_suffix("")
        module = ".".join(relative.parts)
        modules.add(module)
        if module.endswith(".__init__"):
            modules.add(module.removesuffix(".__init__"))

    for path in python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module
            if module and module.startswith("app."):
                assert module in modules or any(
                    candidate.startswith(module + ".")
                    for candidate in modules
                ), (path, module)


def check_router_registry() -> None:
    text = (ROOT / "app/bot/handlers/__init__.py").read_text(encoding="utf-8")
    required = (
        "admin_router",
        "admin_marketing_router",
        "source_management_router",
        "start_marketing_router",
        "start_router",
        "questions_router",
        "subscriptions_router",
        "reveals_router",
        "answers_router",
        "errors_router",
    )
    for name in required:
        assert text.count(f"include_router({name})") == 1, name


def check_no_artifacts() -> None:
    forbidden = (
        list(ROOT.glob(".stage*-install"))
        + list(ROOT.glob(".audit-*-backup"))
        + list(ROOT.glob("*.bak-before-*"))
        + list(ROOT.glob(".env.before-*"))
        + list(ROOT.glob("anonmake-stage-*.zip*"))
    )
    assert not forbidden, [str(path.relative_to(ROOT)) for path in forbidden]
    assert not (ROOT / "anonmake.db").exists()
    assert not (ROOT / "AUDIT_REPORT.md").exists()
    assert not (ROOT / "REAUDIT_REPORT.md").exists()


def check_current_admin() -> None:
    ui = (ROOT / "app/bot/ui.py").read_text(encoding="utf-8")
    handler = (ROOT / "app/bot/handlers/admin_stage25_1.py").read_text(
        encoding="utf-8"
    )
    keyboard = (ROOT / "app/bot/keyboards/main_menu.py").read_text(
        encoding="utf-8"
    )

    required = (
        "ADMIN_STATISTICS",
        "ADMIN_BROADCAST",
        "ADMIN_PROFIT",
        "ADMIN_EXPORT",
        "ADMIN_SOURCES",
    )
    for name in required:
        assert name in ui, name
        assert name in handler, name
        assert name in keyboard, name


def check_removed_legacy_modules() -> None:
    removed = (
        "app/services/admin_bi.py",
        "app/services/system_health.py",
        "app/web/metrics.py",
    )
    for relative in removed:
        assert not (ROOT / relative).exists(), relative


def check_runtime_guards() -> None:
    abuse = (ROOT / "app/services/abuse_guard.py").read_text(encoding="utf-8")
    assert "redis.call('INCR'" in abuse
    assert "redis.call('EXPIRE'" in abuse

    delivery = (ROOT / "app/repositories/delivery.py").read_text(encoding="utf-8")
    assert 'dialect == "postgresql"' in delivery
    assert 'dialect == "sqlite"' in delivery


def check_operational_files() -> None:
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "\\n" not in env_example
    assert 'IMPAYA_AUTH_PREFIX="Bearer "' in env_example

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "compose.marketing.yaml" in makefile
    assert "compose.delivery.yaml" in makefile
    assert "release-check" in makefile
    assert "stabilize-check" in makefile

    backup = (ROOT / "scripts/backup_postgres.sh").read_text(encoding="utf-8")
    assert '--file="$TMP_SQL"' in backup


def check_security_guards() -> None:
    marketing = (ROOT / "app/bot/handlers/admin_marketing.py").read_text(
        encoding="utf-8"
    )
    assert marketing.count("not is_admin(") >= 7

    web = (ROOT / "app/web/app.py").read_text(encoding="utf-8")
    assert "def verify_webhook_secret" in web
    assert "settings.impaya_webhook_secret" in web
    assert "Invalid webhook secret" in web
    assert 'text("SELECT 1")' in web


def main() -> None:
    count = check_python_syntax()
    check_local_imports()
    check_router_registry()
    check_no_artifacts()
    check_current_admin()
    check_removed_legacy_modules()
    check_runtime_guards()
    check_operational_files()
    check_security_guards()
    print("Project check: OK")
    print(f"Python files parsed: {count}")
    print("Local imports: verified")
    print("Router registry: clean")
    print("Development artifacts: removed")
    print("Admin UI registry: synchronized")
    print("Runtime and security guards: verified")
    print("Operational files: verified")


if __name__ == "__main__":
    main()
