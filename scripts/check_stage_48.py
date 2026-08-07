from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, (path, needle)


def main() -> None:
    require(
        "app/core/worker_health.py",
        "mark_worker_heartbeat",
        "heartbeat_age_seconds",
    )
    require(
        "scripts/worker_healthcheck.py",
        "Worker healthcheck: OK",
        "--max-age",
    )
    require(
        "app/delivery_worker.py",
        'mark_worker_heartbeat("delivery-worker"',
    )
    require(
        "app/broadcast_worker.py",
        'mark_worker_heartbeat("broadcast-worker"',
    )
    require(
        "compose.delivery.yaml",
        "scripts.worker_healthcheck",
        "delivery-worker",
    )
    require(
        "compose.marketing.yaml",
        "scripts.worker_healthcheck",
        "broadcast-worker",
    )
    require(
        "app/web/admin_observability.py",
        '@router.get("/observability"',
        '"/observability/delivery/{job_id}/retry"',
        '"/observability/delivery/unlock-stale"',
    )
    require(
        "app/web/templates/platform_observability.html",
        "Наблюдаемость и ошибки",
        "Последние неудачные доставки",
        "Ошибки платежей",
    )
    require(
        "app/web/templates/base.html",
        "/admin/platform/observability",
        "admin-ui.css?v=48",
    )

    print("Stage 48 check: OK")
    print("Worker heartbeat healthchecks: ready")
    print("Observability and error center: ready")
    print("Delivery retry and stale-lock recovery: ready")
    print("No database migration required")


if __name__ == "__main__":
    main()
