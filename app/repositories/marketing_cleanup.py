from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketing import TrafficSource


class MarketingCleanupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def source(self, source_id: int) -> TrafficSource | None:
        return await self.session.get(TrafficSource, source_id)

    async def delete_source(self, source_id: int) -> bool:
        """Archive a source while preserving historical attribution."""
        source = await self.session.get(TrafficSource, source_id)
        if source is None or not source.is_active:
            return False

        source.is_active = False
        await self.session.flush()
        return True
