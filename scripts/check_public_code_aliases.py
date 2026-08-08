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

    migration_21 = (ROOT / "migrations/versions/20260807_0021_short_public_codes.py").read_text(encoding="utf-8")
    assert 'SNAPSHOT_TABLE = "public_code_rotation_snapshot"' in migration_21
    assert '_snapshot_current_codes("before_0021")' in migration_21
    assert "new_code not in historical" in migration_21

    migration_23 = (ROOT / "migrations/versions/20260808_0023_random_short_public_codes.py").read_text(encoding="utf-8")
    assert 'SNAPSHOT_TABLE = "public_code_rotation_snapshot"' in migration_23
    assert '_snapshot_current_codes("before_0023")' in migration_23
    assert "new_code not in historical" in migration_23

    migration_27 = (ROOT / "migrations/versions/20260808_0027_public_code_aliases.py").read_text(encoding="utf-8")
    assert 'revision = "20260808_0027"' in migration_27
    assert 'down_revision = "20260808_0026"' in migration_27
    assert "def _import_snapshot()" in migration_27
    assert "Historical public-code alias conflicts" in migration_27
    assert "INSERT INTO user_public_code_aliases" in migration_27
    assert "DROP TABLE {SNAPSHOT_TABLE}" in migration_27

    print("Public code alias check: OK")
    print("0021 snapshots pre-rotation public codes")
    print("0023 snapshots intermediate public codes and reserves all historical codes")
    print("0027 imports bridge snapshots into permanent project-scoped aliases")
    print("New public codes avoid reserved historical aliases")


if __name__ == "__main__":
    main()
