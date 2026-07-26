from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketing import SourceAttribution, TrafficSource


class MarketingCleanupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def source(self, source_id: int) -> TrafficSource | None:
        return await self.session.get(TrafficSource, source_id)

    async def delete_source(self, source_id: int) -> bool:
        source = await self.session.get(TrafficSource, source_id)
        if source is None:
            return False

        await self.session.execute(
            delete(SourceAttribution).where(
                SourceAttribution.source_id == source_id
            )
        )
        await self.session.delete(source)
        return True
