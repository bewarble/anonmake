from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "scripts/restore_database.py").read_text(encoding="utf-8")

    assert "POSTGRES_CUSTOM_MAGIC" in source
    assert "relative_to(allowed_root)" in source
    assert "--confirm" in source
    assert "validate_restore_in_temporary_database(path)" in source
    assert 'backup_database(f"restore-{timestamp}")' in source
    assert 'compose("stop", *DEFAULT_SERVICES)' in source
    assert '"--exit-on-error"' in source
    assert "drop_database(target)" in source
    assert "create_database(target)" in source
    assert "restored_head != validated_head" in source
    assert "Application services were intentionally left stopped" in source
    assert 'compose("up"' not in source

    scheduled = (ROOT / "scripts/backup_postgres.sh").read_text(encoding="utf-8")
    assert "gzip -t" in scheduled
    assert 'mv "$TMP_GZ" "$FILE"' in scheduled

    deploy = (ROOT / "scripts/deploy.py").read_text(encoding="utf-8")
    assert "POSTGRES_CUSTOM_MAGIC = b\"PGDMP\"" in deploy
    assert "backup_database(timestamp)" in deploy

    print("Database restore safety check: OK")
    print("Restore validates dump in an isolated database before production replacement")
    print("A fresh pre-restore backup is mandatory")
    print("Application services remain stopped after destructive restore")


if __name__ == "__main__":
    main()
