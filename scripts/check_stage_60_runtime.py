from app.core.platform_health import runtime_health_snapshot


def main() -> None:
    rows = runtime_health_snapshot()
    assert rows, "runtime health snapshot is empty"

    unhealthy = [
        f"{row.service}:{row.status}"
        for row in rows
        if row.status != "healthy"
    ]
    assert not unhealthy, f"runtime heartbeat is not healthy: {unhealthy}"

    for row in rows:
        age = "unknown" if row.age_seconds is None else f"{row.age_seconds}s"
        print(f"Stage 60 runtime: {row.service}: {row.status} ({row.state}, age={age})")

    print("Stage 60 runtime check: OK")


if __name__ == "__main__":
    main()
