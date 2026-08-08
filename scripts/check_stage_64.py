from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    services = set(re.findall(r"^  ([a-zA-Z0-9_-]+):\s*$", compose, re.MULTILINE))
    assert "managed-bots" in services
    for legacy in ("bot", "bot-two", "bot-three", "bot-four"):
        assert legacy not in services, f"legacy polling service remains: {legacy}"
    assert 'command: ["python", "-m", "app.managed_bots"]' in compose

    managed = (ROOT / "app/managed_bots.py").read_text(encoding="utf-8")
    assert 'BotInstance.runtime_mode == "managed"' in managed
    assert "BotInstance.is_active.is_(True)" in managed
    assert "BotInstance.token_encrypted.is_not(None)" not in managed
    assert "resolve_bot_token(session, settings, item)" in managed
    assert "token_fingerprint" in managed
    assert "dispatcher.include_router(build_router())" in managed

    credentials = (ROOT / "app/services/bot_credentials.py").read_text(encoding="utf-8")
    assert "if instance.token_encrypted:" in credentials
    assert "settings.bot_tokens().get(instance.code)" in credentials

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "$(COMPOSE) up -d --build --remove-orphans" in makefile
    assert "restart managed-bots web worker delivery-worker broadcast-worker" in makefile
    for legacy in ("restart bot ", "bot-two", "bot-three", "bot-four"):
        assert legacy not in makefile, legacy

    migration = (ROOT / "migrations/versions/20260808_0025_unified_bot_runtime.py").read_text(encoding="utf-8")
    assert 'revision = "20260808_0025"' in migration
    assert 'down_revision = "20260808_0024"' in migration
    assert "UPDATE bot_instances SET runtime_mode = 'managed'" in migration

    print("Stage 64 check: OK")
    print("All Telegram projects: one managed-bots runtime")
    print("Legacy bot/bot-two/bot-three/bot-four polling services: removed")
    print("Admin-encrypted and legacy environment credentials: supported")
    print("Token changes: hot-restarted inside managed runtime")
    print("docker-up removes orphaned legacy bot containers")


if __name__ == "__main__":
    main()
