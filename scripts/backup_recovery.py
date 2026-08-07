from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shlex
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "backups" / "deploy"
MAGIC = b"PGDMP"
COMPOSE_FILES = (
    "compose.yaml",
    "compose.backup.yaml",
    "compose.delivery.yaml",
    "compose.marketing.yaml",
)


def compose_command(*args: str) -> list[str]:
    command = ["docker", "compose"]
    for filename in COMPOSE_FILES:
        command.extend(("-f", filename))
    command.extend(args)
    return command


def backup_path(name: str) -> Path:
    candidate = Path(name).name
    if candidate != name or not candidate.endswith(".dump"):
        raise SystemExit("Укажите только имя .dump-файла из backups/deploy.")
    path = BACKUP_DIR / candidate
    if not path.is_file():
        raise SystemExit(f"Резервная копия не найдена: {candidate}")
    return path


def valid_custom_dump(path: Path) -> bool:
    try:
        if path.stat().st_size <= len(MAGIC):
            return False
        with path.open("rb") as stream:
            return stream.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def list_backups() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        BACKUP_DIR.glob("*.dump"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not files:
        print("Резервные копии отсутствуют.")
        return

    for path in files:
        stat = path.stat()
        created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        status = "OK" if valid_custom_dump(path) else "INVALID"
        print(f"{status:7} {stat.st_size:>10} {created} {path.name}")


def verify_backup(name: str) -> None:
    path = backup_path(name)
    if not valid_custom_dump(path):
        raise SystemExit(f"Проверка не пройдена: {path.name}")
    print(f"Резервная копия имеет PostgreSQL custom format: {path.name}")
    print(f"Размер: {path.stat().st_size} байт")


def restore_plan(name: str) -> None:
    path = backup_path(name)
    if not valid_custom_dump(path):
        raise SystemExit("Нельзя подготовить восстановление: dump не прошёл проверку формата.")

    stop = compose_command(
        "stop",
        "web",
        "worker",
        "delivery-worker",
        "broadcast-worker",
        "managed-bots",
    )
    restore = compose_command(
        "exec",
        "-T",
        "db",
        "pg_restore",
        "-U",
        os.getenv("POSTGRES_USER", "anonmake"),
        "-d",
        os.getenv("POSTGRES_DB", "anonmake"),
        "--clean",
        "--if-exists",
    )

    print("План аварийного восстановления (команды НЕ выполняются):")
    print("1. Создать дополнительный свежий backup текущей БД.")
    print("2. Остановить сервисы приложения:")
    print("   " + " ".join(shlex.quote(x) for x in stop))
    print("3. Передать dump в pg_restore через stdin:")
    print(
        "   cat "
        + shlex.quote(str(path))
        + " | "
        + " ".join(shlex.quote(x) for x in restore)
    )
    print("4. Запустить migrate, затем сервисы и release-check-runtime.")
    print("5. Проверить /health, Telegram-доставку и Impaya до открытия трафика.")
    print()
    print("Stage 49 намеренно не выполняет production restore автоматически.")


def run(command: list[str], *, input_file=None, capture: bool = False) -> subprocess.CompletedProcess:
    print("$", " ".join(shlex.quote(item) for item in command))
    return subprocess.run(
        command,
        cwd=ROOT,
        stdin=input_file,
        text=False if input_file is not None else True,
        capture_output=capture,
        check=True,
    )


def restore_drill(name: str) -> None:
    path = backup_path(name)
    if not valid_custom_dump(path):
        raise SystemExit("Restore drill отменён: dump не прошёл проверку формата.")

    user = os.getenv("POSTGRES_USER", "anonmake")
    maintenance_db = os.getenv("POSTGRES_DB", "anonmake")
    drill_db = f"anonmake_recovery_{uuid.uuid4().hex[:10]}"

    create = compose_command(
        "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-U", user,
        "-d", maintenance_db, "-c", f'CREATE DATABASE "{drill_db}";',
    )
    restore = compose_command(
        "exec", "-T", "db", "pg_restore", "-U", user, "-d", drill_db,
        "--no-owner", "--no-privileges", "--exit-on-error",
    )
    inspect = compose_command(
        "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-U", user,
        "-d", drill_db, "-Atc",
        "SELECT version_num FROM alembic_version; SELECT count(*) FROM information_schema.tables WHERE table_schema='public';",
    )
    drop = compose_command(
        "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-U", user,
        "-d", maintenance_db, "-c", f'DROP DATABASE IF EXISTS "{drill_db}" WITH (FORCE);',
    )

    print(f"Изолированная проверка восстановления: {path.name}")
    print(f"Временная БД: {drill_db}")
    try:
        run(create)
        with path.open("rb") as stream:
            run(restore, input_file=stream)
        result = run(inspect, capture=True)
        output = result.stdout.decode() if isinstance(result.stdout, bytes) else result.stdout
        print("Проверка восстановленной БД:")
        print((output or "").strip())
        print("Restore drill: OK")
    finally:
        try:
            run(drop)
        except subprocess.CalledProcessError:
            print(f"ВНИМАНИЕ: не удалось автоматически удалить временную БД {drill_db}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Проверка резервных копий и безопасное восстановление")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="показать резервные копии")
    verify = sub.add_parser("verify", help="проверить сигнатуру dump")
    verify.add_argument("name")
    plan = sub.add_parser("plan", help="показать план production-восстановления без выполнения")
    plan.add_argument("name")
    drill = sub.add_parser("drill", help="восстановить dump во временную БД, проверить и удалить её")
    drill.add_argument("name")
    args = parser.parse_args()

    if args.command == "list":
        list_backups()
    elif args.command == "verify":
        verify_backup(args.name)
    elif args.command == "plan":
        restore_plan(args.name)
    elif args.command == "drill":
        restore_drill(args.name)


if __name__ == "__main__":
    main()
