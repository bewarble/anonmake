from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.core.worker_health import heartbeat_age_seconds, read_worker_heartbeat
from app.database.session import SessionFactory, close_database


async def check_database() -> None:
    async with SessionFactory() as session:
        value = (await session.execute(text("SELECT 1"))).scalar_one()
        if value != 1:
            raise RuntimeError("Unexpected database healthcheck response")


async def main() -> None:
    parser = argparse.ArgumentParser(description="AnonMake worker liveness check")
    parser.add_argument("service")
    parser.add_argument("--max-age", type=float, default=90.0)
    args = parser.parse_args()

    try:
        payload = read_worker_heartbeat(args.service)
        age = heartbeat_age_seconds(args.service)
        if age > args.max_age:
            raise RuntimeError(
                f"Worker heartbeat is stale: service={args.service} age={age:.1f}s"
            )
        await check_database()
        print(
            "Worker healthcheck: OK",
            f"service={args.service}",
            f"age={age:.1f}s",
            f"pid={payload.get('pid', '-')}",
        )
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
