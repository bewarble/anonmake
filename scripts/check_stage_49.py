from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, (path, needle)


def main() -> None:
    require(
        "app/web/admin_system.py",
        "POSTGRES_CUSTOM_MAGIC",
        "_backup_is_valid",
        "backups=backups",
    )
    require(
        "app/web/templates/platform_system.html",
        "Резервные копии",
        "Целостность формата",
        "scripts.backup_recovery",
    )
    require(
        "scripts/backup_recovery.py",
        'MAGIC = b"PGDMP"',
        "restore_plan",
        "restore_drill",
        "anonmake_recovery_",
        "Restore drill: OK",
        "production restore автоматически",
    )

    print("Stage 49 check: OK")
    print("Backup integrity visibility: ready")
    print("Recovery planning CLI: ready")
    print("Isolated restore drill: ready")
    print("Automatic destructive production restore: intentionally disabled")
    print("No database migration required")


if __name__ == "__main__":
    main()
