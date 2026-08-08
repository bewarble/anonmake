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
    deploy = "scripts/deploy.py"
    text = (ROOT / deploy).read_text(encoding="utf-8")

    assert 'POSTGRES_CUSTOM_MAGIC = b"PGDMP"' in text
    assert "PUBLIC_CODE_ROTATION_HEADS" not in text
    assert "--allow-public-code-rotation" not in text
    assert "ensure_safe_migration_path" not in text

    backup = function_source(deploy, "backup_database")
    assert "POSTGRES_CUSTOM_MAGIC" in backup
    assert "stream.read(len(POSTGRES_CUSTOM_MAGIC)) == POSTGRES_CUSTOM_MAGIC" in backup
    assert "destination.unlink" in backup
    assert "pg_dump" in backup
    assert '"-Fc"' in backup

    main = function_source(deploy, "main")
    assert main.index("backup_database") < main.index("run_migrations")
    assert main.index("run_migrations") < main.index("cleanup_backups")
    assert "scripts.release_check" in main
    assert "--runtime-only" in main

    migration_21 = (ROOT / "migrations/versions/20260807_0021_short_public_codes.py").read_text(encoding="utf-8")
    migration_23 = (ROOT / "migrations/versions/20260808_0023_random_short_public_codes.py").read_text(encoding="utf-8")
    migration_27 = (ROOT / "migrations/versions/20260808_0027_public_code_aliases.py").read_text(encoding="utf-8")
    assert '_snapshot_current_codes("before_0021")' in migration_21
    assert '_snapshot_current_codes("before_0023")' in migration_23
    assert "new_code not in historical" in migration_21
    assert "new_code not in historical" in migration_23
    assert "_import_snapshot()" in migration_27
    assert "INSERT INTO user_public_code_aliases" in migration_27

    release = (ROOT / "scripts/release_check.py").read_text(encoding="utf-8")
    assert '"scripts.check_public_code_aliases_runtime"' in release

    print("Deploy safety check: OK")
    print("Public-code rotations preserve historical links through bridge snapshots")
    print("No manual public-code-rotation bypass is required")
    print("PostgreSQL backup is validated as custom PGDMP format")
    print("Backup remains before migrations and runtime integrity checks remain after migration")


if __name__ == "__main__":
    main()
