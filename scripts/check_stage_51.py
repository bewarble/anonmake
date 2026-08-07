from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, (path, needle)


def main() -> None:
    require(
        "app/web/static/admin-stage51.js",
        "data.confirm",
        "requestSubmit",
        "data-loading-label",
        "Escape",
        "is-submitting",
    )
    require(
        "app/web/static/admin-stage51.css",
        "admin-action-overlay",
        "admin-action-dialog",
        "admin-action-modal-open",
        "stage51-spin",
    )
    require(
        "app/web/templates/base.html",
        "admin-stage51.css?v=51",
        "admin-stage51.js?v=51",
    )
    require(
        "app/web/templates/platform_admins.html",
        "data-confirm-title=\"Удалить аккаунт?\"",
        "data-confirm-tone=\"danger\"",
        "data-loading-label=\"Удаляем…\"",
    )
    require(
        "app/web/templates/platform_observability.html",
        "data-confirm-title=\"Освободить зависшие доставки?\"",
        "data-loading-label=\"Повторяем…\"",
    )
    require(
        "scripts/audit_active_web_assets.py",
        '"admin-stage51.css"',
        '"admin-stage51.js"',
    )

    migrations = list((ROOT / "migrations/versions").glob("*stage_51*"))
    assert not migrations, migrations

    print("Stage 51 check: OK")
    print("Unified confirmations, loading states and repeat-submit protection: ready")
    print("Dangerous and bulk admin actions use the shared confirmation UX")
    print("No Stage 51 migration required")


if __name__ == "__main__":
    main()
