from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.bot_instance import BotInstance
from app.models.delivery import DeliveryOutbox


class DeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(
        self,
        *,
        kind: str,
        dedupe_key: str,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
        payload: dict | None = None,
        bot_id: int | None = None,
    ) -> DeliveryOutbox:
        resolved_bot_id = bot_id or require_current_bot().id
        bind = self.session.get_bind()
        dialect = bind.dialect.name
        if dialect == "postgresql":
            insert = postgresql_insert
        elif dialect == "sqlite":
            insert = sqlite_insert
        else:
            raise RuntimeError(f"Unsupported delivery database dialect: {dialect}")

        statement = (
            insert(DeliveryOutbox)
            .values(
                bot_id=resolved_bot_id,
                kind=kind,
                dedupe_key=dedupe_key,
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                payload=payload,
                status="pending",
                next_attempt_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(index_elements=["bot_id", "dedupe_key"])
            .returning(DeliveryOutbox)
        )
        result = await self.session.execute(statement)
        created = result.scalar_one_or_none()
        if created is not None:
            return created

        existing = await self.session.scalar(
            select(DeliveryOutbox).where(
                DeliveryOutbox.bot_id == resolved_bot_id,
                DeliveryOutbox.dedupe_key == dedupe_key,
            )
        )
        if existing is None:
            raise RuntimeError("Delivery outbox conflict without existing row")
        return existing

    async def claim_batch(
        self,
        *,
        worker_id: str,
        limit: int,
        stale_after_seconds: int,
    ) -> list[DeliveryOutbox]:
        now = datetime.now(timezone.utc)
        stale_before = now - timedelta(seconds=stale_after_seconds)
        deliverable_bot_ids = select(BotInstance.id).where(
            BotInstance.is_active.is_(True),
            BotInstance.is_maintenance.is_(False),
        )

        statement = (
            select(DeliveryOutbox)
            .where(
                DeliveryOutbox.bot_id.in_(deliverable_bot_ids),
                DeliveryOutbox.status.in_(("pending", "retry")),
                or_(
                    DeliveryOutbox.next_attempt_at.is_(None),
                    DeliveryOutbox.next_attempt_at <= now,
                ),
                or_(
                    DeliveryOutbox.locked_at.is_(None),
                    DeliveryOutbox.locked_at < stale_before,
                ),
            )
            .order_by(DeliveryOutbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(statement)
        jobs = list(result.scalars())

        for job in jobs:
            job.status = "processing"
            job.locked_at = now
            job.locked_by = worker_id

        await self.session.flush()
        return jobs

    async def mark_delivered(
        self,
        job: DeliveryOutbox,
        *,
        telegram_message_id: int,
    ) -> None:
        job.status = "delivered"
        job.telegram_message_id = telegram_message_id
        job.delivered_at = datetime.now(timezone.utc)
        job.locked_at = None
        job.locked_by = None
        job.last_error = None

    async def mark_retry(
        self,
        job: DeliveryOutbox,
        *,
        error: str,
        delay_seconds: int,
    ) -> None:
        job.attempts += 1
        job.status = "retry"
        job.next_attempt_at = datetime.now(timezone.utc) + timedelta(
            seconds=delay_seconds
        )
        job.locked_at = None
        job.locked_by = None
        job.last_error = error[:1000]

    async def mark_paused(
        self,
        job: DeliveryOutbox,
        *,
        reason: str,
        delay_seconds: int = 30,
    ) -> None:
        """Return a claimed job to the queue without consuming a retry attempt."""
        job.status = "retry"
        job.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        job.locked_at = None
        job.locked_by = None
        job.last_error = reason[:1000]

    async def mark_failed(
        self,
        job: DeliveryOutbox,
        *,
        error: str,
    ) -> None:
        job.attempts += 1
        job.status = "failed"
        job.locked_at = None
        job.locked_by = None
        job.last_error = error[:1000]
