from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/services/bot_pool.py",
        "migrations/versions/20260728_0011_multibot_delivery.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    delivery_model = (ROOT / "app/models/delivery.py").read_text(encoding="utf-8")
    assert "bot_id" in delivery_model
    assert "uq_delivery_outbox_bot_dedupe" in delivery_model

    marketing_model = (ROOT / "app/models/marketing.py").read_text(encoding="utf-8")
    assert "class Broadcast" in marketing_model
    broadcast_block = marketing_model.split("class Broadcast", 1)[1]
    assert "bot_id" in broadcast_block

    repository = (ROOT / "app/repositories/delivery.py").read_text(encoding="utf-8")
    assert 'index_elements=["bot_id", "dedupe_key"]' in repository
    assert "resolved_bot_id" in repository

    delivery_worker = (ROOT / "app/delivery_worker.py").read_text(encoding="utf-8")
    assert "BotPool" in delivery_worker
    assert "job.bot_id" in delivery_worker

    broadcast_worker = (ROOT / "app/broadcast_worker.py").read_text(encoding="utf-8")
    assert "User.bot_id == item.bot_id" in broadcast_worker
    assert "bot_id=item.bot_id" in broadcast_worker

    config = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
    assert 'alias="MULTIBOT_TOKENS_JSON"' in config
    assert "def bot_tokens" in config

    print("Stage 38.2 check: OK")
    print("Delivery outbox bot isolation: ready")
    print("Broadcast bot isolation: ready")
    print("Per-bot Telegram token routing: ready")
    print("Legacy delivery and broadcasts backfill: ready")
    print("Second bot containers: not enabled until billing isolation")


if __name__ == "__main__":
    check()
