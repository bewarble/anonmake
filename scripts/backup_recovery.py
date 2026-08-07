from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "backups" / "deploy"
MAGIC = b"PGDMP"
COMPOSE_FILES = (
    "compose.yaml",
    "compose.backup.yaml",
    "compose.delivery.yaml",
    "compose.marketing.yaml",
)


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

    compose = ["docker", "compose"]
    for filename in COMPOSE_FILES:
        compose.extend(("-f", filename))

    stop = [*compose, "stop", "web", "worker", "delivery-worker", "broadcast-worker", "managed-bots"]
    restore = [
        *compose,
        "exec",
        "-T",
        "db",
        "pg_restore",
        "-U",
        "anonmake",
        "-d",
        "anonmake",
        "--clean",
        "--if-exists",
    ]

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
    print("Stage 49 намеренно не выполняет restore автоматически.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Проверка резервных копий и безопасный план восстановления")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="показать резервные копии")
    verify = sub.add_parser("verify", help="проверить сигнатуру dump")
    verify.add_argument("name")
    plan = sub.add_parser("plan", help="показать план восстановления без выполнения")
    plan.add_argument("name")
    args = parser.parse_args()

    if args.command == "list":
        list_backups()
    elif args.command == "verify":
        verify_backup(args.name)
    elif args.command == "plan":
        restore_plan(args.name)


if __name__ == "__main__":
    main()
