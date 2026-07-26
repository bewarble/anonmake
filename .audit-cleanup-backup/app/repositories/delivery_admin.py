from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery import DeliveryOutbox


class DeliveryAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self) -> dict[str, int]:
        rows = await self.session.execute(
            select(
                DeliveryOutbox.status,
                func.count(DeliveryOutbox.id),
            ).group_by(DeliveryOutbox.status)
        )
        result = {
            "pending": 0,
            "processing": 0,
            "retry": 0,
            "delivered": 0,
            "failed": 0,
        }
        for status, count in rows:
            result[str(status)] = int(count)
        return result

    async def recent_failed(self, limit: int = 10) -> list[DeliveryOutbox]:
        result = await self.session.execute(
            select(DeliveryOutbox)
            .where(DeliveryOutbox.status == "failed")
            .order_by(DeliveryOutbox.id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def retry_failed(self, delivery_id: int) -> bool:
        job = await self.session.get(DeliveryOutbox, delivery_id)
        if job is None or job.status != "failed":
            return False

        job.status = "retry"
        job.next_attempt_at = datetime.now(timezone.utc)
        job.locked_at = None
        job.locked_by = None
        job.last_error = None
        await self.session.flush()
        return True
