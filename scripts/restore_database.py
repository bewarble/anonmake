from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys

from scripts.deploy import (
    COMPOSE_FILES,
    DEFAULT_SERVICES,
    POSTGRES_CUSTOM_MAGIC,
    ROOT,
    backup_database,
    compose,
)


class RestoreError(RuntimeError):
    pass


SAFE_DATABASE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
BACKUPS_ROOT = ROOT / "backups"


def compose_command(*args: str) -> list[str]:
    command = ["docker", "compose"]
    for file_name in COMPOSE_FILES:
        command.extend(("-f", file_name))
    command.extend(args)
    return command


def validate_database_name(value: str) -> str:
    if not SAFE_DATABASE_NAME.fullmatch(value) or value == "postgres":
        raise RestoreError(f"Unsafe PostgreSQL database name: {value!r}")
    return value


def validate_backup(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    allowed_root = BACKUPS_ROOT.resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise RestoreError(
            f"Restore accepts only backups under {allowed_root}"
        ) from exc
    if not resolved.is_file():
        raise RestoreError(f"Backup does not exist: {resolved}")
    with resolved.open("rb") as stream:
        if stream.read(len(POSTGRES_CUSTOM_MAGIC)) != POSTGRES_CUSTOM_MAGIC:
            raise RestoreError("Backup is not a PostgreSQL custom-format dump (PGDMP)")
    return resolved


def database_command(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    command = compose_command("exec", "-T", "db", *args)
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=True,
    )


def restore_dump(path: Path, database: str) -> None:
    database = validate_database_name(database)
    command = compose_command(
        "exec",
        "-T",
        "db",
        "pg_restore",
        "--exit-on-error",
        "--no-owner",
        "--no-privileges",
        "-U",
        os.getenv("POSTGRES_USER", "anonmake"),
        "-d",
        database,
    )
    print(f"$ {' '.join(command)} < {path}", flush=True)
    with path.open("rb") as stream:
        subprocess.run(command, cwd=ROOT, stdin=stream, check=True)


def drop_database(database: str) -> None:
    database = validate_database_name(database)
    user = os.getenv("POSTGRES_USER", "anonmake")
    database_command(
        "psql",
        "-U",
        user,
        "-d",
        "postgres",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        (
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{database}' AND pid <> pg_backend_pid();"
        ),
    )
    database_command("dropdb", "-U", user, "--if-exists", database)


def create_database(database: str) -> None:
    database = validate_database_name(database)
    database_command("createdb", "-U", os.getenv("POSTGRES_USER", "anonmake"), database)


def alembic_head(database: str) -> str:
    database = validate_database_name(database)
    result = database_command(
        "psql",
        "-U",
        os.getenv("POSTGRES_USER", "anonmake"),
        "-d",
        database,
        "-Atc",
        "SELECT version_num FROM alembic_version ORDER BY version_num;",
        capture=True,
    )
    return result.stdout.strip().replace("\n", ",")


def validate_restore_in_temporary_database(path: Path) -> str:
    temporary = validate_database_name(f"anonmake_restore_check_{os.getpid()}")
    try:
        drop_database(temporary)
        create_database(temporary)
        restore_dump(path, temporary)
        head = alembic_head(temporary)
        if not head:
            raise RestoreError("Test restore has no Alembic version")
        print(f"Test restore: OK (Alembic {head})")
        return head
    finally:
        try:
            drop_database(temporary)
        except Exception:
            print(
                f"WARNING: could not remove temporary database {temporary}",
                file=sys.stderr,
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail-safe restore of an AnonMake PostgreSQL custom backup"
    )
    parser.add_argument("backup", type=Path)
    parser.add_argument(
        "--confirm",
        required=True,
        help="Must exactly equal the backup filename",
    )
    args = parser.parse_args()

    path = validate_backup(args.backup)
    if args.confirm != path.name:
        raise RestoreError(
            "Confirmation mismatch. Pass --confirm with the exact backup filename."
        )

    target = validate_database_name(os.getenv("POSTGRES_DB", "anonmake"))

    # Never destroy production before proving that pg_restore can consume the
    # selected dump completely in an isolated database.
    validated_head = validate_restore_in_temporary_database(path)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safety_backup = backup_database(f"restore-{timestamp}")
    print(f"Pre-restore safety backup: {safety_backup}")

    # Stop all application processes that can hold connections or mutate data.
    # PostgreSQL itself remains running so the restore can be performed inside
    # the existing database container.
    compose("stop", *DEFAULT_SERVICES)

    try:
        drop_database(target)
        create_database(target)
        restore_dump(path, target)
        restored_head = alembic_head(target)
        if restored_head != validated_head:
            raise RestoreError(
                f"Restored Alembic head {restored_head!r} differs from validated "
                f"head {validated_head!r}"
            )
    except Exception:
        print(
            "RESTORE FAILED. Application services remain stopped. "
            f"Safety backup is {safety_backup}.",
            file=sys.stderr,
        )
        raise

    print("\nDatabase restore completed successfully.")
    print(f"Restored Alembic head: {restored_head}")
    print(f"Safety backup of replaced database: {safety_backup}")
    print("Application services were intentionally left stopped.")
    print(
        "After verifying the restored database, start services explicitly with "
        "the normal docker compose command or perform a controlled deploy."
    )


if __name__ == "__main__":
    main()
