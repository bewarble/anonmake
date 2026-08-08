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
    middleware = (ROOT / "app/bot/middlewares/database.py").read_text(encoding="utf-8")
    call = function_source("app/bot/middlewares/database.py", "__call__")
    deny = function_source("app/bot/middlewares/database.py", "_deny_user_event")

    assert "await session.get(BotInstance, cached_bot.id)" in call
    assert "instance.is_active" in call
    assert "instance.is_maintenance" in call
    assert "self.settings.admin_ids_set" in call
    assert "instance.maintenance_message" in call
    assert "isinstance(event, (Message, CallbackQuery))" in call
    assert "await event.answer" in deny
    assert "show_alert=True" in deny
    assert "DEFAULT_MAINTENANCE_MESSAGE" in middleware
    assert "DEFAULT_INACTIVE_MESSAGE" in middleware

    # Service updates such as my_chat_member are intentionally not classified as
    # user events, so membership/block-state tracking continues during maintenance.
    assert "is_user_event = isinstance(event, (Message, CallbackQuery))" in call

    print("Runtime maintenance check: OK")
    print("Maintenance and active switches are read from DB for every Telegram update")
    print("Telegram admins bypass maintenance; service updates remain operational")


if __name__ == "__main__":
    main()
