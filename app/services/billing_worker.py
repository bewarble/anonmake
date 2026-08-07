from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time

from app.core.performance import WORKER_BATCHES, WORKER_BATCH_SIZE
from app.core.worker_health import mark_worker_heartbeat
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
        client: ImpayaClient | None = None,
        client_factory=None,
        interval_seconds: int = 60,
        *,
        automatic_charges_enabled: bool = False,
        batch_size: int = 100,
        **options,
    ) -> None:
        self.client = client
        self.client_factory = client_factory
        self.interval_seconds = interval_seconds
        self.automatic_charges_enabled = automatic_charges_enabled
        self.batch_size = batch_size
        self.options = options
        self._stop = asyncio.Event()

    async def run(self) -> None:
        mark_worker_heartbeat(
            "billing-worker",
            state="started",
            automatic_charges_enabled=self.automatic_charges_enabled,
        )
        if not self.automatic_charges_enabled:
            logger.warning(
                "Automatic recurrent charges are disabled "
                "(BILLING_AUTOMATIC_CHARGES_ENABLED=false)"
            )

        while not self._stop.is_set():
            started = time.monotonic()
            try:
                mark_worker_heartbeat(
                    "billing-worker",
                    state="processing",
                    automatic_charges_enabled=self.automatic_charges_enabled,
                )
                stats = await self.tick()
                duration_ms = int((time.monotonic() - started) * 1000)
                WORKER_BATCHES.labels("billing", "completed").inc()
                WORKER_BATCH_SIZE.labels("billing").observe(stats.due)
                mark_worker_heartbeat(
                    "billing-worker",
                    state="idle",
                    automatic_charges_enabled=self.automatic_charges_enabled,
                    due=stats.due,
                    success=stats.success,
                    pending=stats.pending,
                    failed=stats.failed,
                    expired=stats.expired,
                    duration_ms=duration_ms,
                )
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
                    duration_ms,
                )
            except Exception as exc:
                WORKER_BATCHES.labels("billing", "failed").inc()
                mark_worker_heartbeat(
                    "billing-worker",
                    state="error",
                    exception_type=type(exc).__name__,
                    automatic_charges_enabled=self.automatic_charges_enabled,
                )
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

                owned_client = None
                try:
                    client = self.client
                    if self.client_factory is not None:
                        owned_client = await self.client_factory(
                            session, subscription.bot_id
                        )
                        client = owned_client
                    if client is None:
                        raise RuntimeError("Impaya client is not configured")
                    result = await BillingService(
                        session,
                        client,
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
                finally:
                    if owned_client is not None:
                        await owned_client.close()

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
