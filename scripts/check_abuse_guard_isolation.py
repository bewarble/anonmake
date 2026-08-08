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
    source = (ROOT / "app/services/abuse_guard.py").read_text(encoding="utf-8")
    namespace = function_source("app/services/abuse_guard.py", "_namespace")
    check = function_source("app/services/abuse_guard.py", "check_question")
    rollback = function_source("app/services/abuse_guard.py", "rollback_duplicate")

    assert "require_current_bot().id" in namespace
    assert 'f"{bot_id}:{sender_telegram_id}"' in namespace
    assert "self._namespace(sender_telegram_id)" in check
    assert "self._namespace(sender_telegram_id)" in rollback
    assert "abuse:question:burst" in source
    assert "abuse:question:minute" in source
    assert "abuse:question:duplicate" in source

    print("Abuse guard isolation check: OK")
    print("Rate limits and duplicate detection are isolated per Telegram project")


if __name__ == "__main__":
    main()
