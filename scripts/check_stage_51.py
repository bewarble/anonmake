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
        "form.dataset.confirm",
        "requestSubmit",
        "dataset.loadingLabel",
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
        "admin-stage51.css?v=",
        "admin-stage51.js?v=",
    )
    require(
        "app/web/templates/platform_admins.html",
        "data-confirm-title",
        "data-confirm-tone",
        "data-loading-label",
    )
    require(
        "app/web/templates/platform_observability.html",
        "data-confirm-title",
        "data-loading-label",
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
    print("Shared confirmation UX is wired to sensitive and bulk admin actions")
    print("No Stage 51 migration required")


if __name__ == "__main__":
    main()
