from pathlib import Path

required_files = {
    "Dockerfile",
    "docker-entrypoint.sh",
    "compose.yaml",
    ".dockerignore",
    "Makefile",
}

missing = sorted(path for path in required_files if not Path(path).exists())
assert not missing, missing

compose = Path("compose.yaml").read_text(encoding="utf-8")
for service in ("db:", "migrate:", "bot:", "web:", "worker:"):
    assert service in compose, service

assert "service_completed_successfully" in compose
assert 'command: ["python", "-m", "scripts.migrate"]' in compose
assert "127.0.0.1" in compose
assert "POSTGRES_PASSWORD" in compose

entrypoint = Path("docker-entrypoint.sh").read_text(encoding="utf-8")
assert "scripts.migrate" not in entrypoint
assert 'exec "$@"' in entrypoint

dockerignore = Path(".dockerignore").read_text(encoding="utf-8")
assert ".env" in dockerignore
assert "__pycache__" in dockerignore

print("Stage 6 check: OK")
print("Compose services: db, migrate, bot, web, worker")
print("Migrations: single dedicated service")
print("Web port: bound to localhost by default")
