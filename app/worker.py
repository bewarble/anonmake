from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from app.core.config import load_settings
from app.database.session import close_database, init_database
from app.services.billing_worker import BillingWorker
from app.services.impaya_factory import create_impaya_client, load_impaya_config


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

    async def client_factory(session, bot_id: int):
        config = await load_impaya_config(session, settings, bot_id)
        return create_impaya_client(config)

    worker = BillingWorker(
        client_factory=client_factory,
        interval_seconds=settings.billing_worker_interval_seconds,
        automatic_charges_enabled=settings.billing_automatic_charges_enabled,
        batch_size=settings.billing_worker_batch_size,
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
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
