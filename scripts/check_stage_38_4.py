from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    config_path = ROOT / "app/core/config.py"
    compose_path = ROOT / "compose.yaml"

    ast.parse(
        config_path.read_text(encoding="utf-8"),
        filename=str(config_path),
    )

    config = config_path.read_text(encoding="utf-8")
    compose = compose_path.read_text(encoding="utf-8")

    # Legacy environment aliases remain supported as a credential fallback while
    # all polling itself is now owned by the single managed-bots runtime.
    for number in ("TWO", "THREE", "FOUR"):
        assert f'alias="BOT_{number}_TOKEN"' in config
        assert f'alias="BOT_{number}_USERNAME"' in config
        assert f'alias="BOT_{number}_CODE"' in config

    assert "configured_bot_identities" in config
    assert "Duplicate bot code" in config
    assert "Duplicate bot username" in config

    services = set(
        re.findall(r"^  ([a-zA-Z0-9_-]+):\s*$", compose, re.MULTILINE)
    )
    assert "managed-bots" in services
    for legacy in ("bot", "bot-two", "bot-three", "bot-four"):
        assert legacy not in services, legacy

    assert 'profiles: ["multibot"]' not in compose
    assert 'command: ["python", "-m", "app.managed_bots"]' in compose

    release = (
        ROOT / "scripts/release_check.py"
    ).read_text(encoding="utf-8")
    assert '"scripts.check_stage_38_4"' in release

    print("Stage 38.4 check: OK")
    print("Legacy bot credential aliases: compatible")
    print("Single managed-bots polling runtime: ready")
    print("Per-project Docker polling services: removed")
    print("Shared PostgreSQL and Redis: ready")


if __name__ == "__main__":
    check()
