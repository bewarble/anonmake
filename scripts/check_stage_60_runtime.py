from app.core.platform_health import runtime_health_snapshot


def main() -> None:
    rows = runtime_health_snapshot()
    assert rows, "runtime health snapshot is empty"
    down = [row.service for row in rows if row.status == "down"]
    assert not down, f"stale runtime heartbeat: {down}"

    for row in rows:
        age = "unknown" if row.age_seconds is None else f"{row.age_seconds}s"
        print(f"Stage 60 runtime: {row.service}: {row.status} ({row.state}, age={age})")

    print("Stage 60 runtime check: OK")


if __name__ == "__main__":
    main()
