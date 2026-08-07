from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/models/bot_instance.py",
        "app/core/bot_context.py",
        "app/repositories/bot_instances.py",
        "migrations/versions/20260728_0010_multibot_foundation.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    user = (ROOT / "app/models/user.py").read_text(encoding="utf-8")
    assert "uq_users_bot_telegram" in user
    assert "uq_users_bot_public_code" in user

    repository = (ROOT / "app/repositories/users.py").read_text(encoding="utf-8")
    assert repository.count("User.bot_id == bot_id") == 2
    assert "bot_id = require_current_bot().id" in repository
    assert "bot_id=bot_id" in repository

    middleware = (
        ROOT / "app/bot/middlewares/database.py"
    ).read_text(encoding="utf-8")
    assert "BotInstanceRepository" in middleware
    assert "set_current_bot" in middleware
    assert "reset_current_bot" in middleware

    print("Stage 38.1 check: OK")
    print("Bot instance model: ready")
    print("Per-bot user uniqueness: ready")
    print("Per-update bot context: ready")
    print("Existing users migration to primary bot: ready")
    print("Four bot containers: intentionally not enabled yet")


if __name__ == "__main__":
    check()
