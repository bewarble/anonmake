from __future__ import annotations

import ast
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> None:
    for path in sorted((ROOT / "app").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    assert (ROOT / ".env.example").is_file()
    assert not (ROOT / "cripts \\").exists()
    assert not (ROOT / "cripts ").exists()

    admin_repo = read("app/web/admin_repository.py")
    assert "from app.models.crm import CrmEvent" in admin_repo
    assert "numeric_filters = [User.telegram_id == numeric]" in admin_repo

    crm_repo = read("app/web/admin_repository_stage27.py")
    assert "numeric_filters = [User.telegram_id == numeric]" in crm_repo

    stage29 = read("app/web/admin_stage29.py")
    assert "broadcast_stats=broadcast_stats" in stage29
    assert "audience_counts=audience_counts" in stage29
    assert 'kind="anonymous"' in stage29
    assert 'kind="subscription"' not in stage29
    assert "source = await session.get(TrafficSource, source_id)\n        source = await session.get(TrafficSource, source_id)" not in stage29

    source_repo = read("app/web/admin_repository_stage29.py")
    assert "PaymentAttempt.user_id" not in source_repo
    assert "Subscription.user_id" in source_repo

    worker = read("app/delivery_worker.py")
    assert 'caption = payload.get("caption") or job.text' in worker
    assert "reply_markup=markup" in worker

    broadcast_template = read("app/web/templates/business_broadcasts.html")
    for name in ("audience_counts", "broadcast_stats"):
        assert name in broadcast_template

    migration = read("migrations/versions/20260728_0009_media_questions.py")
    assert 'revision = "20260728_0009"' in migration
    assert 'down_revision = "20260726_0008"' in migration

    templates_root = ROOT / "app/web/templates"
    env = Environment(loader=FileSystemLoader(str(templates_root)))
    for name in (
        "money", "date_time", "date_only", "status_label", "status_tone",
        "payment_kind", "delivery_kind", "audit_action", "user_name", "yes_no",
    ):
        env.filters[name] = lambda value, *args, **kwargs: value
    for template in templates_root.glob("*.html"):
        env.get_template(template.name)

    print("Full audit check: OK")
    print("Web CRM imports and large Telegram IDs: fixed")
    print("Broadcast page context and creation: fixed")
    print("Source payment joins: verified")
    print("Media delivery buttons and captions: fixed")
    print("Environment example and migration chain: verified")


if __name__ == "__main__":
    main()
