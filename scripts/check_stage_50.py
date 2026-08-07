from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    ROOT / "app/web/admin_error_ux.py",
    ROOT / "app/web/templates/admin_error.html",
    ROOT / "app/web/static/admin-stage50.css",
    ROOT / "docs/STAGE_50_ADMIN_ERROR_UX.md",
)


def require(path: Path, *needles: str) -> None:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise SystemExit(f"Stage 50 check failed: {path.relative_to(ROOT)} missing {needle!r}")


def main() -> None:
    for path in REQUIRED_FILES:
        if not path.is_file():
            raise SystemExit(f"Stage 50 check failed: missing {path.relative_to(ROOT)}")

    error_module = ROOT / "app/web/admin_error_ux.py"
    ast.parse(error_module.read_text(encoding="utf-8"), filename=str(error_module))
    require(
        error_module,
        "ERROR_TITLES",
        "403:",
        "404:",
        "409:",
        "422:",
        "500:",
        "new_error_id",
        "action=\"web_error\"",
        "route",
        "admin",
        "project",
        "install_admin_error_ux",
        "RequestValidationError",
    )
    require(
        ROOT / "app/web/templates/admin_error.html",
        "Идентификатор ошибки",
        "data-copy-error-id",
        "admin-stage50.css",
    )
    require(
        ROOT / "app/web/templates/base.html",
        "admin-flash",
        "flash_tone",
        "admin-stage50.css",
    )
    require(
        ROOT / "app/web/admin_observability.py",
        "AdminAuditLog.action == \"web_error\"",
        "recent_admin_errors",
        "redirect_with_flash",
    )
    require(
        ROOT / "app/web/templates/platform_observability.html",
        "Последние ошибки админки",
        "item.error_id",
        "item.route",
    )
    require(
        ROOT / "app/web/admin_system.py",
        "install_admin_error_ux(web_app)",
    )

    migrations = list((ROOT / "migrations/versions").glob("*stage_50*"))
    if migrations:
        raise SystemExit("Stage 50 check failed: Stage 50 must not add a migration")

    print("Stage 50 check: OK")
    print("Admin error pages, error_id audit events, flash UX and observability are wired.")
    print("No Stage 50 migration detected.")


if __name__ == "__main__":
    main()
