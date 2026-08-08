from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.marketing import TrafficSource


class MarketingCleanupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def source(self, source_id: int) -> TrafficSource | None:
        bot_id = require_current_bot().id
        return await self.session.scalar(
            select(TrafficSource).where(
                TrafficSource.id == source_id,
                TrafficSource.bot_id == bot_id,
            )
        )

    async def delete_source(self, source_id: int) -> bool:
        """Archive a source while preserving historical attribution."""
        source = await self.source(source_id)
        if source is None or not source.is_active:
            return False

        source.is_active = False
        await self.session.flush()
        return True
