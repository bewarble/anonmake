from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time

from app.database.session import SessionFactory
from app.models.billing import Subscription
from app.repositories.billing import BillingRepository
from app.services.billing import BillingService, ChargeDecision
from app.services.impaya import ImpayaClient

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TickStats:
    due: int = 0
    locked: int = 0
    skipped: int = 0
    success: int = 0
    insufficient: int = 0
    pending: int = 0
    failed: int = 0
    expired: int = 0


class BillingWorker:
    def __init__(
        self,
        client: ImpayaClient,
        interval_seconds: int = 60,
        *,
        automatic_charges_enabled: bool = False,
        batch_size: int = 100,
        **options,
    ) -> None:
        self.client = client
        self.interval_seconds = interval_seconds
        self.automatic_charges_enabled = automatic_charges_enabled
        self.batch_size = batch_size
        self.options = options
        self._stop = asyncio.Event()

    async def run(self) -> None:
        if not self.automatic_charges_enabled:
            logger.warning(
                "Automatic recurrent charges are disabled "
                "(BILLING_AUTOMATIC_CHARGES_ENABLED=false)"
            )

        while not self._stop.is_set():
            started = time.monotonic()
            try:
                stats = await self.tick()
                logger.info(
                    "Billing tick completed due=%s locked=%s skipped=%s "
                    "success=%s insufficient=%s pending=%s failed=%s "
                    "expired=%s duration_ms=%s",
                    stats.due,
                    stats.locked,
                    stats.skipped,
                    stats.success,
                    stats.insufficient,
                    stats.pending,
                    stats.failed,
                    stats.expired,
                    int((time.monotonic() - started) * 1000),
                )
            except Exception:
                logger.exception("Billing worker tick failed")

            try:
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=self.interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    async def tick(self) -> TickStats:
        stats = TickStats()
        now = datetime.now(timezone.utc)

        async with SessionFactory() as session:
            repo = BillingRepository(session)
            stats.expired = await repo.expire_finished_access(now)

            if not self.automatic_charges_enabled:
                return stats

            subscription_ids = await repo.due_subscription_ids(
                now,
                limit=self.batch_size,
            )
            stats.due = len(subscription_ids)

        for subscription_id in subscription_ids:
            await self._process_one(subscription_id, stats)

        return stats

    async def _process_one(
        self,
        subscription_id: int,
        stats: TickStats,
    ) -> None:
        async with SessionFactory() as session:
            repo = BillingRepository(session)
            locked = await repo.try_subscription_lock(subscription_id)
            if not locked:
                stats.skipped += 1
                return

            stats.locked += 1
            try:
                subscription = await session.get(
                    Subscription,
                    subscription_id,
                )
                now = datetime.now(timezone.utc)
                if (
                    subscription is None
                    or not subscription.auto_renew
                    or subscription.next_charge_at is None
                    or subscription.next_charge_at > now
                ):
                    stats.skipped += 1
                    return

                method = await repo.payment_method_for_user(
                    subscription.user_id
                )
                if (
                    method is None
                    or not method.is_active
                    or not method.is_recurrent
                    or not method.binding_id
                    or not method.impaya_user_id
                ):
                    stats.skipped += 1
                    return

                try:
                    result = await BillingService(
                        session,
                        self.client,
                        **self.options,
                    ).renew(subscription, method)
                except Exception:
                    await session.rollback()
                    stats.failed += 1
                    logger.exception(
                        "Subscription renewal failed subscription=%s",
                        subscription.id,
                    )
                    return

                if result.decision == ChargeDecision.SUCCESS:
                    stats.success += 1
                elif result.decision == ChargeDecision.INSUFFICIENT:
                    stats.insufficient += 1
                elif result.decision == ChargeDecision.PENDING:
                    stats.pending += 1
                else:
                    stats.failed += 1

                logger.info(
                    "Renewal processed subscription=%s decision=%s attempt=%s",
                    subscription.id,
                    result.decision.value,
                    result.attempt.id,
                )
            finally:
                try:
                    await repo.release_subscription_lock(subscription_id)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    logger.exception(
                        "Failed to release billing lock subscription=%s",
                        subscription_id,
                    )

    def stop(self) -> None:
        self._stop.set()
