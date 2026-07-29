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

ROOT = Path(__file__).resolve().parents[1]
VAR_DIR = ROOT / "var"
BACKUP_DIR = ROOT / "backups" / "deploy"
STATE_FILE = VAR_DIR / "deploy-state.json"
LOG_FILE = VAR_DIR / "deploy-history.jsonl"
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
    command.extend(("--profile", "multibot"))
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
    if result.returncode != 0 or destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        raise DeployError("Не удалось создать резервную копию PostgreSQL.")
    print(f"Резервная копия: {destination} ({destination.stat().st_size} байт)")
    return destination


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
    parser.add_argument("--health-timeout", type=int, default=120)
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

    try:
        ensure_clean_git(args.allow_dirty)
        run([sys.executable, "-m", "scripts.release_check"])
        compose("config", "--quiet")
        source_head = alembic_head_from_source()
        database_head_before = current_database_head()

        if not args.skip_backup:
            backup_path = backup_database(timestamp)

        if not args.skip_build:
            compose("build", *services)

        compose("run", "--rm", "migrate")
        compose("up", "-d", "--force-recreate", "--no-deps", *services)
        wait_for_web(args.health_timeout)
        compose("exec", "-T", "web", "python", "-m", "scripts.release_check", "--runtime-only")

        database_head_after = current_database_head()
        if database_head_after != source_head:
            raise DeployError(
                f"Версия БД {database_head_after!r} не совпадает с Alembic head {source_head!r}."
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
            "services": service_snapshot(services),
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
            "alembic_head": source_head or None,
            "previous_alembic_head": database_head_before or None,
            "backup_path": str(backup_path.relative_to(ROOT)) if backup_path else None,
            "error": str(exc),
            "services": service_snapshot(services),
        }
        write_state(payload)
        print(f"\nДеплой остановлен: {exc}", file=sys.stderr)
        print("Предыдущие контейнеры не удаляются автоматически; резервная копия сохранена.", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
