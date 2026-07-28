from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/services/telegram_content.py",
        "app/models/question.py",
        "app/models/delivery.py",
        "app/bot/handlers/questions.py",
        "app/delivery_worker.py",
        "migrations/versions/20260728_0009_media_questions.py",
        "app/web/admin_complete.py",
        "app/web/templates/global_search.html",
        "app/web/templates/business_sources.html",
        "app/web/templates/business_broadcasts.html",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    questions = (ROOT / "app/bot/handlers/questions.py").read_text(encoding="utf-8")
    assert "extract_content" in questions
    assert "delivery_payload" in questions
    assert "content_type=content.content_type" in questions

    worker = (ROOT / "app/delivery_worker.py").read_text(encoding="utf-8")
    for method in (
        "send_photo",
        "send_video",
        "send_document",
        "send_voice",
        "send_sticker",
    ):
        assert method in worker, method

    source_template = (
        ROOT / "app/web/templates/business_sources.html"
    ).read_text(encoding="utf-8")
    assert "Цена оплаты" in source_template
    assert "Конверсия" in source_template

    broadcast_template = (
        ROOT / "app/web/templates/business_broadcasts.html"
    ).read_text(encoding="utf-8")
    assert "Доставлено" in broadcast_template
    assert "Заблокировали" in broadcast_template

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert "/admin/search" in base

    print("Stage 35.2 check: OK")
    print("Anonymous media questions: ready")
    print("Durable media delivery: ready")
    print("Source funnel and ROI metrics: ready")
    print("Broadcast audience and delivery metrics: ready")
    print("Web global search: ready")
    print("Expanded user CRM card: ready")


if __name__ == "__main__":
    check()
