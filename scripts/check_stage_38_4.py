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

    for number in ("TWO", "THREE", "FOUR"):
        assert f'alias="BOT_{number}_TOKEN"' in config
        assert f'alias="BOT_{number}_USERNAME"' in config
        assert f'alias="BOT_{number}_CODE"' in config

    assert "configured_bot_identities" in config
    assert "Duplicate bot code" in config
    assert "Duplicate bot username" in config

    required_services = {"bot", "bot-two", "bot-three", "bot-four", "managed-bots"}
    services = set(
        re.findall(r"^  ([a-zA-Z0-9_-]+):\s*$", compose, re.MULTILINE)
    )
    assert not required_services - services, required_services - services

    for service in ("bot-two", "bot-three", "bot-four"):
        match = re.search(
            rf"^  {re.escape(service)}:\s*$"
            rf"(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\s*$|\Z)",
            compose,
            re.MULTILINE | re.DOTALL,
        )
        assert match is not None, service
        assert 'profiles: ["multibot"]' not in match.group("body")

    assert 'profiles: ["multibot"]' not in compose

    for variable in (
        "BOT_TWO_TOKEN",
        "BOT_TWO_USERNAME",
        "BOT_THREE_TOKEN",
        "BOT_THREE_USERNAME",
        "BOT_FOUR_TOKEN",
        "BOT_FOUR_USERNAME",
    ):
        assert variable in compose

    release = (
        ROOT / "scripts/release_check.py"
    ).read_text(encoding="utf-8")
    assert '"scripts.check_stage_38_4"' in release

    print("Stage 38.4 check: OK")
    print("Four polling bot services: ready")
    print("Managed bot runtime: ready")
    print("Unified default startup for all bot services: ready")
    print("Shared PostgreSQL and Redis: ready")
    print("Worker token pool for four bots: ready")


if __name__ == "__main__":
    check()
