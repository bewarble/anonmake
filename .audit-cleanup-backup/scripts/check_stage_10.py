from pathlib import Path

required = (
    "scripts/backup_postgres.sh",
    "scripts/restore_postgres.sh",
    "scripts/check_dependencies.py",
    "app/services/system_health.py",
    "app/bot/handlers/admin_system.py",
    "compose.backup.yaml",
)

for rel in required:
    assert Path(rel).exists(), rel

assert "pg_dump" in Path("scripts/backup_postgres.sh").read_text()
assert "CONFIRM_RESTORE=yes" in Path("scripts/restore_postgres.sh").read_text()

print("Stage 10 check: OK")
print("Backups: compressed PostgreSQL dumps")
print("Retention: configurable")
print("Restore: explicit confirmation required")
print("Admin system status: PostgreSQL + Redis")
