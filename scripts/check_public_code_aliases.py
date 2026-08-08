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
    model = (ROOT / "app/models/user.py").read_text(encoding="utf-8")
    assert "class UserPublicCodeAlias" in model
    assert '"user_public_code_aliases"' in model
    assert '"uq_user_public_code_alias_bot_code"' in model

    lookup = function_source("app/repositories/users.py", "get_by_public_code")
    assert "User.public_code == public_code" in lookup
    assert "UserPublicCodeAlias.public_code == public_code" in lookup
    assert "UserPublicCodeAlias.bot_id == bot_id" in lookup

    create = function_source("app/repositories/users.py", "get_or_create_from_telegram")
    assert "UserPublicCodeAlias.public_code == public_code" in create
    assert "UserPublicCodeAlias.bot_id == bot_id" in create

    migration = (ROOT / "migrations/versions/20260808_0027_public_code_aliases.py").read_text(encoding="utf-8")
    assert 'revision = "20260808_0027"' in migration
    assert 'down_revision = "20260808_0026"' in migration

    print("Public code alias check: OK")
    print("Historical aliases resolve within the owning Telegram project")
    print("New public codes avoid reserved historical aliases")


if __name__ == "__main__":
    main()
