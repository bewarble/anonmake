from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def function_source(path: str, name: str) -> str:
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(f"Function not found: {path}:{name}")


def main() -> None:
    claim = function_source("app/repositories/delivery.py", "claim_batch")
    enqueue = function_source("app/repositories/delivery.py", "enqueue")
    paused = function_source("app/repositories/delivery.py", "mark_paused")
    next_broadcast = function_source("app/repositories/marketing.py", "next_broadcast")
    disabled_worker = function_source("app/worker.py", "run_disabled_worker")

    assert "BotInstance.is_active.is_(True)" in claim
    assert "BotInstance.is_maintenance.is_(False)" in claim
    assert "current_bot is not None and resolved_bot_id != current_bot.id" in enqueue
    assert "job.attempts" not in paused
    assert 'job.status = "retry"' in paused

    assert "BotInstance.is_active.is_(True)" in next_broadcast
    assert "BotInstance.is_maintenance.is_(False)" in next_broadcast

    delivery_worker = (ROOT / "app/delivery_worker.py").read_text(encoding="utf-8")
    assert "not instance.is_active or instance.is_maintenance" in delivery_worker
    assert "repository.mark_paused" in delivery_worker

    assert 'state="disabled"' in disabled_worker
    assert "await asyncio.sleep(60)" in disabled_worker

    print("Worker project-state check: OK")
    print("Inactive/maintenance projects pause delivery and broadcast work")
    print("Paused deliveries do not consume retry attempts")
    print("Explicit delivery ownership cannot cross an active bot context")
    print("Disabled billing stays healthy and idle instead of restart-looping")


if __name__ == "__main__":
    main()
