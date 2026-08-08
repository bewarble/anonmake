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
    assert '"20260729_0019"' in text
    assert '"20260807_0020"' in text
    assert '"20260807_0021"' in text
    assert '"20260808_0022"' in text
    assert '"--allow-public-code-rotation"' in text

    guard = function_source(deploy, "ensure_safe_migration_path")
    assert "PUBLIC_CODE_ROTATION_HEADS" in guard
    assert "allow_public_code_rotation" in guard
    assert "raise DeployError" in guard
    assert "инвалидируют ранее опубликованные" in guard

    backup = function_source(deploy, "backup_database")
    assert "POSTGRES_CUSTOM_MAGIC" in backup
    assert "stream.read(len(POSTGRES_CUSTOM_MAGIC)) == POSTGRES_CUSTOM_MAGIC" in backup
    assert "destination.unlink" in backup
    assert "pg_dump" in backup
    assert '"-Fc"' in backup

    main = function_source(deploy, "main")
    assert "ensure_safe_migration_path" in main
    assert main.index("ensure_safe_migration_path") < main.index("backup_database")
    assert main.index("backup_database") < main.index("run_migrations")
    assert main.index("run_migrations") < main.index("cleanup_backups")

    migration_21 = (ROOT / "migrations/versions/20260807_0021_short_public_codes.py").read_text(encoding="utf-8")
    migration_23 = (ROOT / "migrations/versions/20260808_0023_random_short_public_codes.py").read_text(encoding="utf-8")
    assert "_regenerate(8)" in migration_21
    assert "_regenerate(5, 6)" in migration_23

    print("Deploy safety check: OK")
    print("Pre-0023 databases fail closed before public-code rotation")
    print("PostgreSQL backup is validated as custom PGDMP format")
    print("Backup remains before migrations and retention remains after success")


if __name__ == "__main__":
    main()
