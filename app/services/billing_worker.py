from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging

from app.database.session import SessionFactory
from app.repositories.billing import BillingRepository
from app.services.billing import BillingService
from app.services.impaya import ImpayaClient

logger = logging.getLogger(__name__)


class BillingWorker:
    def __init__(self, client: ImpayaClient, interval_seconds: int = 60) -> None:
        self.client = client
        self.interval_seconds = interval_seconds
        self._stop = asyncio.Event()

    async def run(self) -> None:
        while not self._stop.is_set():
            try:
                await self.tick()
            except Exception:
                logger.exception("Billing worker tick failed")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.interval_seconds
                )
            except asyncio.TimeoutError:
                pass

    async def tick(self) -> None:
        async with SessionFactory() as session:
            repo = BillingRepository(session)
            due = await repo.due_subscriptions(datetime.now(timezone.utc))
            for subscription in due:
                method = await repo.payment_method_for_user(subscription.user_id)
                if not method or not method.is_active or not method.is_recurrent:
                    continue
                service = BillingService(session, self.client)
                await service.renew(subscription, method)

    def stop(self) -> None:
        self._stop.set()
