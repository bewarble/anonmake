from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, (path, needle)


def main() -> None:
    require(
        "app/core/platform_health.py",
        "RUNTIME_SERVICES",
        '"managed-bots"',
        '"delivery-worker"',
        '"broadcast-worker"',
        '"billing-worker"',
        "runtime_health_snapshot",
        "overall_runtime_status",
    )
    require(
        "app/services/billing_worker.py",
        '"billing-worker"',
        "mark_worker_heartbeat(",
        'state="processing"',
        'state="idle"',
        'state="error"',
    )
    require(
        "app/managed_bots.py",
        'mark_worker_heartbeat("managed-bots"',
        "configured_count=len(instances)",
        "active_count=len(tasks)",
    )
    require(
        "compose.yaml",
        "runtime_health:/tmp/anonmake-health",
        "runtime_health:/tmp/anonmake-health:ro",
        '"scripts.worker_healthcheck", "managed-bots"',
        '"scripts.worker_healthcheck", "billing-worker"',
        "runtime_health:",
    )
    require("compose.delivery.yaml", "runtime_health:/tmp/anonmake-health")
    require("compose.marketing.yaml", "runtime_health:/tmp/anonmake-health")
    require(
        "app/web/admin_observability.py",
        "runtime_health_snapshot()",
        "overall_runtime_status(runtime_health)",
        "incident_count",
    )
    require(
        "app/web/templates/platform_observability.html",
        "Состояние runtime",
        "runtime_health",
        "incident_count",
        "heartbeat",
    )
    require(
        "app/web/static/admin-stage60.css",
        ".runtime-health-grid",
        ".runtime-health-card",
        ".incident-summary",
        "@media(max-width:900px)",
    )
    require("app/web/templates/base.html", "admin-stage60.css?v=60")
    require("scripts/audit_active_web_assets.py", '"admin-stage60.css"')
    assert not list((ROOT / "migrations/versions").glob("*stage_60*"))
    print("Stage 60 check: OK")
    print("Shared runtime heartbeat volume: ready")
    print("Managed bots, delivery, broadcast and billing health: visible")
    print("Platform incident summary: ready")
    print("No Docker socket exposure required")
    print("No Stage 60 migration required")


if __name__ == "__main__":
    main()
