from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.worker_health import read_worker_heartbeat


@dataclass(frozen=True, slots=True)
class RuntimeHealth:
    service: str
    label: str
    status: str
    state: str
    age_seconds: int | None
    timestamp: str | None
    details: dict[str, object]


RUNTIME_SERVICES: tuple[tuple[str, str, int], ...] = (
    ("delivery-worker", "Доставка", 90),
    ("broadcast-worker", "Рассылки", 90),
    ("billing-worker", "Биллинг", 180),
)


def _age_seconds(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - timestamp).total_seconds()))


def runtime_health_snapshot() -> list[RuntimeHealth]:
    rows: list[RuntimeHealth] = []
    for service, label, max_age in RUNTIME_SERVICES:
        try:
            payload = read_worker_heartbeat(service)
        except (OSError, ValueError, RuntimeError):
            rows.append(
                RuntimeHealth(
                    service=service,
                    label=label,
                    status="unknown",
                    state="Нет heartbeat",
                    age_seconds=None,
                    timestamp=None,
                    details={},
                )
            )
            continue

        age = _age_seconds(payload.get("timestamp"))
        state = str(payload.get("state") or "unknown")[:80]
        if age is None:
            status = "unknown"
        elif age > max_age * 2:
            status = "down"
        elif age > max_age:
            status = "degraded"
        else:
            status = "healthy"

        safe_details = {
            str(key)[:80]: value
            for key, value in payload.items()
            if key not in {"service", "timestamp", "pid"}
            and isinstance(value, (str, int, float, bool))
        }
        rows.append(
            RuntimeHealth(
                service=service,
                label=label,
                status=status,
                state=state,
                age_seconds=age,
                timestamp=payload.get("timestamp") if isinstance(payload.get("timestamp"), str) else None,
                details=safe_details,
            )
        )
    return rows


def overall_runtime_status(rows: list[RuntimeHealth]) -> str:
    statuses = {row.status for row in rows}
    if "down" in statuses:
        return "down"
    if "degraded" in statuses or "unknown" in statuses:
        return "degraded"
    return "healthy"
