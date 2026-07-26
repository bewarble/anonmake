from __future__ import annotations

import asyncio
import logging

from app.core.config import load_settings
from app.database.session import close_database, init_database
from app.services.billing_worker import BillingWorker
from app.services.impaya import ImpayaClient


async def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if not settings.billing_enabled:
        logging.getLogger(__name__).warning(
            "BILLING_ENABLED=false; worker exits without charging"
        )
        return

    client = ImpayaClient(
        settings.impaya_api_url,
        settings.impaya_api_token,
        settings.impaya_terminal_name,
        auth_header=settings.impaya_auth_header,
        auth_prefix=settings.impaya_auth_prefix,
        protocol_version=settings.impaya_protocol_version,
    )
    worker = BillingWorker(
        client,
        interval_seconds=settings.billing_worker_interval_seconds,
    )

    await init_database()
    try:
        await worker.run()
    finally:
        await client.close()
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
