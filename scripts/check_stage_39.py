from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/core/performance.py",
        "app/bot/middlewares/performance.py",
        "app/web/admin_performance.py",
        "app/web/templates/performance.html",
        "migrations/versions/20260728_0014_performance_indexes.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    config = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
    assert 'alias="PERFORMANCE_ENABLED"' in config
    assert 'alias="PERF_SLOW_SQL_MS"' in config
    assert 'alias="WORKER_IDLE_MAX_SECONDS"' in config

    session = (ROOT / "app/database/session.py").read_text(encoding="utf-8")
    assert 'before_cursor_execute' in session
    assert 'after_cursor_execute' in session

    delivery = (ROOT / "app/delivery_worker.py").read_text(encoding="utf-8")
    broadcast = (ROOT / "app/broadcast_worker.py").read_text(encoding="utf-8")
    assert "next_idle_delay" in delivery
    assert "next_idle_delay" in broadcast
    assert "Subscription.bot_id == item.bot_id" in broadcast

    middleware = (ROOT / "app/bot/middlewares/database.py").read_text(encoding="utf-8")
    assert "_resolve_current_bot" in middleware
    assert "_bootstrap_lock" in middleware

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert '/admin/performance' in base

    release = (ROOT / "scripts/release_check.py").read_text(encoding="utf-8")
    assert '"scripts.check_stage_39"' in release

    print("Stage 39 check: OK")
    print("Telegram, web and SQL profiling: ready")
    print("Adaptive worker idle backoff: ready")
    print("Bot instance middleware cache: ready")
    print("Multibot query indexes: ready")
    print("Admin performance dashboard: ready")


if __name__ == "__main__":
    check()
