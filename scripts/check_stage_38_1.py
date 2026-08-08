from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _function_source(tree: ast.AST, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(f"Function not found: {name}")


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

    repository_path = ROOT / "app/repositories/users.py"
    repository = repository_path.read_text(encoding="utf-8")
    repository_tree = ast.parse(repository, filename=str(repository_path))

    # Every public lookup by a user identifier must be scoped to the current bot.
    # Do not assert an exact text occurrence count: strengthening isolation by
    # adding another scoped lookup must never make this release check fail.
    for method_name in (
        "get_by_id",
        "get_by_telegram_id",
        "get_by_public_code",
    ):
        method = _function_source(repository_tree, method_name)
        assert "require_current_bot().id" in method, method_name
        assert "User.bot_id == bot_id" in method, method_name

    create_method = _function_source(repository_tree, "get_or_create_from_telegram")
    assert "require_current_bot().id" in create_method
    assert "bot_id=bot_id" in create_method.replace(" ", "")

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
    print("Scoped user lookups: ready")
    print("Existing users migration to primary bot: ready")
    print("Four bot containers: intentionally not enabled yet")


if __name__ == "__main__":
    check()
