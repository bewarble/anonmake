from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

HEARTBEAT_DIR = Path(os.getenv("WORKER_HEARTBEAT_DIR", "/tmp/anonmake-health"))


def heartbeat_path(service: str) -> Path:
    safe = "".join(ch for ch in service if ch.isalnum() or ch in {"-", "_"})
    if not safe:
        raise ValueError("Worker service name is empty")
    return HEARTBEAT_DIR / f"{safe}.json"


def mark_worker_heartbeat(service: str, **details: object) -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    path = heartbeat_path(service)
    payload = {
        "service": service,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        **details,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def read_worker_heartbeat(service: str) -> dict:
    path = heartbeat_path(service)
    return json.loads(path.read_text(encoding="utf-8"))


def heartbeat_age_seconds(service: str) -> float:
    payload = read_worker_heartbeat(service)
    value = payload.get("timestamp")
    if not isinstance(value, str):
        raise RuntimeError("Heartbeat timestamp is missing")
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - timestamp).total_seconds())
