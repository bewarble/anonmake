from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

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
        trial_amount=settings.trial_price_kopecks,
        trial_duration=timedelta(hours=settings.trial_duration_hours),
        primary_amount=settings.primary_price_kopecks,
        primary_duration=timedelta(days=settings.primary_duration_days),
        fallback_amount=settings.fallback_price_kopecks,
        fallback_duration=timedelta(days=settings.fallback_duration_days),
    )

    await init_database()
    try:
        await worker.run()
    finally:
        await client.close()
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
