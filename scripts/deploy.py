from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Callable, TypeVar

ROOT = Path(__file__).resolve().parents[1]
VAR_DIR = ROOT / "var"
BACKUP_DIR = ROOT / "backups" / "deploy"
STATE_FILE = VAR_DIR / "deploy-state.json"
LOG_FILE = VAR_DIR / "deploy-history.jsonl"
POSTGRES_CUSTOM_MAGIC = b"PGDMP"
PUBLIC_CODE_ROTATION_HEADS = {
    "20260729_0019",
    "20260807_0020",
    "20260807_0021",
    "20260808_0022",
}
COMPOSE_FILES = (
    "compose.yaml",
    "compose.backup.yaml",
    "compose.delivery.yaml",
    "compose.marketing.yaml",
)
DEFAULT_SERVICES = (
    "web",
    "worker",
    "delivery-worker",
    "broadcast-worker",
    "managed-bots",
)
T = TypeVar("T")


class DeployError(RuntimeError):
    pass


def run(
    command: list[str],
    *,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(shlex.quote(item) for item in command)
    print(f"\n$ {printable}", flush=True)
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=check,
    )


def output(command: list[str]) -> str:
    return run(command, capture=True).stdout.strip()


def compose(*args: str, capture: bool = False, check: bool = True):
    command = ["docker", "compose"]
    for file_name in COMPOSE_FILES:
        command.extend(("-f", file_name))
    command.extend(args)
    return run(command, capture=capture, check=check)


def git_value(*args: str) -> str:
    return output(["git", *args])


def ensure_clean_git(allow_dirty: bool) -> None:
    status = git_value("status", "--porcelain")
    if status and not allow_dirty:
        raise DeployError(
            "Рабочее дерево Git содержит незакоммиченные изменения. "
            "Закоммитьте их или запустите с --allow-dirty."
        )


def ensure_safe_migration_path(database_head: str, *, allow_public_code_rotation: bool) -> None:
    heads = {value.strip() for value in database_head.split(",") if value.strip()}
    dangerous = sorted(heads & PUBLIC_CODE_ROTATION_HEADS)
    if dangerous and not allow_public_code_rotation:
        raise DeployError(
            "Автоматический деплой остановлен: текущая БД находится до миграции "
            "20260808_0023, а миграции 0021/0023 перегенерируют public_code у "
            "существующих пользователей и инвалидируют ранее опубликованные "
            "Telegram-ссылки. Сначала подготовьте совместимую миграцию/aliases. "
            "Для осознанного принятия этого breaking change используйте "
            "--allow-public-code-rotation. Текущая версия БД: "
            + ", ".join(dangerous)
        )


def backup_database(timestamp: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    destination = BACKUP_DIR / f"anonmake-before-{timestamp}.dump"
    command = ["docker", "compose"]
    for file_name in COMPOSE_FILES:
        command.extend(("-f", file_name))
    command.extend(
        (
            "exec",
            "-T",
            "db",
            "pg_dump",
            "-U",
            os.getenv("POSTGRES_USER", "anonmake"),
            "-d",
            os.getenv("POSTGRES_DB", "anonmake"),
            "-Fc",
        )
    )
    print(f"\n$ {' '.join(shlex.quote(x) for x in command)} > {destination}")
    with destination.open("wb") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream)
    valid = False
    if result.returncode == 0:
        try:
            with destination.open("rb") as stream:
                valid = stream.read(len(POSTGRES_CUSTOM_MAGIC)) == POSTGRES_CUSTOM_MAGIC
        except OSError:
            valid = False
    if not valid:
        destination.unlink(missing_ok=True)
        raise DeployError("Не удалось создать корректную резервную копию PostgreSQL custom format.")
    print(f"Резервная копия: {destination} ({destination.stat().st_size} байт)")
    return destination


def cleanup_backups(retain: int) -> list[str]:
    if retain <= 0:
        return []
    try:
        backups = sorted(
            BACKUP_DIR.glob("anonmake-before-*.dump"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return []
    removed: list[str] = []
    for path in backups[retain:]:
        try:
            path.unlink()
            removed.append(path.name)
        except OSError:
            continue
    return removed


def alembic_head_from_source() -> str:
    return output([
        sys.executable,
        "-c",
        (
            "from alembic.config import Config; "
            "from alembic.script import ScriptDirectory; "
            "print(','.join(ScriptDirectory.from_config(Config('alembic.ini')).get_heads()))"
        ),
    ])


def current_database_head() -> str:
    result = compose(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        os.getenv("POSTGRES_USER", "anonmake"),
        "-d",
        os.getenv("POSTGRES_DB", "anonmake"),
        "-Atc",
        "SELECT version_num FROM alembic_version ORDER BY version_num;",
        capture=True,
    )
    return result.stdout.strip().replace("\n", ",")


def wait_for_web(timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        result = subprocess.run(
            [
                "curl",
                "-fsS",
                "--max-time",
                "5",
                "http://127.0.0.1:8000/health",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            print("Web healthcheck: OK")
            return
        last_error = result.stderr.strip()
        time.sleep(3)
    raise DeployError(f"Web healthcheck не пройден: {last_error or 'тайм-аут'}")


def service_snapshot(services: tuple[str, ...]) -> dict[str, dict[str, str]]:
    snapshot: dict[str, dict[str, str]] = {}
    for service in services:
        result = compose("ps", "-a", "--format", "json", service, capture=True, check=False)
        if result.returncode != 0 or not result.stdout.strip():
            snapshot[service] = {"state": "unknown", "health": ""}
            continue
        try:
            rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            row = rows[0] if rows else {}
            snapshot[service] = {
                "state": str(row.get("State") or row.get("Status") or "unknown"),
                "health": str(row.get("Health") or ""),
            }
        except json.JSONDecodeError:
            snapshot[service] = {"state": result.stdout.strip(), "health": ""}
    return snapshot


def wait_for_services(services: tuple[str, ...], timeout_seconds: int) -> dict[str, dict[str, str]]:
    deadline = time.monotonic() + timeout_seconds
    last_snapshot: dict[str, dict[str, str]] = {}
    while time.monotonic() < deadline:
        last_snapshot = service_snapshot(services)
        if all(
            info.get("state") == "running" and info.get("health") == "healthy"
            for info in last_snapshot.values()
        ):
            print("Healthcheck сервисов: OK")
            return last_snapshot
        if any(info.get("health") == "unhealthy" for info in last_snapshot.values()):
            break
        time.sleep(3)
    details = ", ".join(
        f"{name}={info.get('state')}/{info.get('health') or '-'}"
        for name, info in last_snapshot.items()
    )
    raise DeployError(f"Не все сервисы стали healthy: {details or 'нет данных'}")


def run_migrations() -> None:
    result = compose("run", "--rm", "migrate", capture=True, check=False)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise DeployError(
            "Миграции завершились с ошибкой"
            + (f": {stderr[-4000:]}" if stderr else ".")
        )


def write_state(payload: dict) -> None:
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(STATE_FILE)
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Безопасный деплой AnonMake")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-backup", action="store_true")
    parser.add_argument(
        "--allow-public-code-rotation",
        action="store_true",
        help="Разрешить breaking migrations 0021/0023, которые меняют ранее опубликованные public_code.",
    )
    parser.add_argument("--health-timeout", type=int, default=120)
    parser.add_argument("--backup-retain", type=int, default=10)
    parser.add_argument(
        "--services",
        nargs="+",
        default=list(DEFAULT_SERVICES),
        help="Сервисы приложения для сборки и пересоздания",
    )
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    timestamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    commit = git_value("rev-parse", "--short=12", "HEAD")
    branch = git_value("branch", "--show-current")
    services = tuple(dict.fromkeys(args.services))
    backup_path: Path | None = None
    source_head = ""
    database_head_before = ""
    current_step = "инициализация"
    step_durations: dict[str, float] = {}
    service_state: dict[str, dict[str, str]] = {}

    def step(name: str, function: Callable[[], T]) -> T:
        nonlocal current_step
        current_step = name
        print(f"\n--- {name} ---", flush=True)
        started = time.monotonic()
        try:
            return function()
        finally:
            step_durations[name] = round(time.monotonic() - started, 2)

    try:
        step("Проверка Git", lambda: ensure_clean_git(args.allow_dirty))
        step("Статические проверки", lambda: run([sys.executable, "-m", "scripts.release_check"]))
        step("Проверка Compose", lambda: compose("config", "--quiet"))
        source_head = step("Чтение Alembic head", alembic_head_from_source)
        database_head_before = step("Чтение версии БД", current_database_head)
        step(
            "Проверка безопасного пути миграции",
            lambda: ensure_safe_migration_path(
                database_head_before,
                allow_public_code_rotation=args.allow_public_code_rotation,
            ),
        )

        if not args.skip_backup:
            backup_path = step("Резервная копия PostgreSQL", lambda: backup_database(timestamp))

        if not args.skip_build:
            step("Сборка образов", lambda: compose("build", *services))

        step("Миграции", run_migrations)
        step(
            "Пересоздание сервисов",
            lambda: compose("up", "-d", "--force-recreate", "--no-deps", "--remove-orphans", *services),
        )
        step("Web healthcheck", lambda: wait_for_web(args.health_timeout))
        service_state = step(
            "Healthcheck сервисов",
            lambda: wait_for_services(services, args.health_timeout),
        )
        step(
            "Runtime проверки",
            lambda: compose("exec", "-T", "web", "python", "-m", "scripts.release_check", "--runtime-only"),
        )

        database_head_after = step("Финальная версия БД", current_database_head)
        if database_head_after != source_head:
            raise DeployError(
                f"Версия БД {database_head_after!r} не совпадает с Alembic head {source_head!r}."
            )

        removed_backups = step(
            "Ротация резервных копий",
            lambda: cleanup_backups(args.backup_retain),
        )
        completed_at = datetime.now(timezone.utc)
        payload = {
            "status": "success",
            "commit": commit,
            "branch": branch,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": round((completed_at - started_at).total_seconds(), 2),
            "alembic_head": database_head_after,
            "previous_alembic_head": database_head_before,
            "backup_path": str(backup_path.relative_to(ROOT)) if backup_path else None,
            "backup_retention": args.backup_retain,
            "removed_backups": removed_backups,
            "steps": step_durations,
            "services": service_state or service_snapshot(services),
        }
        write_state(payload)
        print("\nДеплой успешно завершён.")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception as exc:
        failed_at = datetime.now(timezone.utc)
        payload = {
            "status": "failed",
            "commit": commit,
            "branch": branch,
            "started_at": started_at.isoformat(),
            "completed_at": failed_at.isoformat(),
            "duration_seconds": round((failed_at - started_at).total_seconds(), 2),
            "failed_step": current_step,
            "steps": step_durations,
            "alembic_head": source_head or None,
            "previous_alembic_head": database_head_before or None,
            "backup_path": str(backup_path.relative_to(ROOT)) if backup_path else None,
            "error": str(exc),
            "services": service_snapshot(services),
        }
        write_state(payload)
        print(f"\nДеплой остановлен на шаге «{current_step}»: {exc}", file=sys.stderr)
        print(
            "Предыдущие контейнеры не удаляются автоматически; резервная копия сохранена.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
