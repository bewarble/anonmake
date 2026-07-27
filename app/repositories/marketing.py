from __future__ import annotations

from datetime import datetime, timezone
import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketing import Broadcast, SourceAttribution, TrafficSource
from app.models.user import User


class MarketingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_source(
        self,
        *,
        name: str,
        source_url: str,
        spend_kopecks: int,
        admin_telegram_id: int,
    ) -> TrafficSource:
        source = TrafficSource(
            name=name,
            code=secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12],
            source_url=source_url,
            spend_kopecks=spend_kopecks,
            created_by_telegram_id=admin_telegram_id,
        )
        self.session.add(source)
        await self.session.flush()
        return source

    async def source_by_code(self, code: str) -> TrafficSource | None:
        return await self.session.scalar(
            select(TrafficSource).where(
                TrafficSource.code == code,
                TrafficSource.is_active.is_(True),
            )
        )

    async def register_source_start(
        self,
        *,
        source: TrafficSource,
        user: User,
    ) -> bool:
        """Apply immutable first-touch attribution once.

        Returns True only when a new attribution was stored. The source click
        counter is incremented only for that successful first attribution.
        """
        existing = await self.session.scalar(
            select(SourceAttribution.id).where(
                SourceAttribution.user_id == user.id
            )
        )
        if existing is not None:
            return False

        attribution = SourceAttribution(
            source_id=source.id,
            user_id=user.id,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(attribution)
                await self.session.flush()
        except IntegrityError:
            return False

        source.clicks += 1
        await self.session.flush()
        return True

    async def sources(self, limit: int = 20) -> list[TrafficSource]:
        result = await self.session.execute(
            select(TrafficSource)
            .where(TrafficSource.is_active.is_(True))
            .order_by(TrafficSource.id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def source_stats(self, source_id: int) -> dict[str, int] | None:
        source = await self.session.get(TrafficSource, source_id)
        if source is None:
            return None

        attributed = int(
            await self.session.scalar(
                select(func.count(SourceAttribution.id)).where(
                    SourceAttribution.source_id == source.id
                )
            )
            or 0
        )
        return {
            "clicks": source.clicks,
            "attributed": attributed,
            "spend_kopecks": source.spend_kopecks,
        }

    async def create_broadcast(
        self,
        *,
        kind: str,
        audience: str,
        text: str,
        admin_telegram_id: int,
    ) -> Broadcast:
        if kind != "anonymous":
            raise ValueError("Unsupported broadcast kind")
        if audience not in {"all", "vip", "non_vip"}:
            raise ValueError("Unsupported broadcast audience")
        if not text.strip() or len(text) > 4000:
            raise ValueError("Invalid broadcast text")

        item = Broadcast(
            kind=kind,
            audience=audience,
            text=text,
            status="queued",
            created_by_telegram_id=admin_telegram_id,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def recent_broadcasts(self, limit: int = 10) -> list[Broadcast]:
        result = await self.session.execute(
            select(Broadcast).order_by(Broadcast.id.desc()).limit(limit)
        )
        return list(result.scalars())

    async def next_broadcast(self) -> Broadcast | None:
        result = await self.session.execute(
            select(Broadcast)
            .where(Broadcast.status.in_(("queued", "processing")))
            .order_by(Broadcast.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return result.scalar_one_or_none()

    async def mark_broadcast_started(self, item: Broadcast) -> None:
        if item.status == "queued":
            item.status = "processing"
            item.started_at = datetime.now(timezone.utc)

    async def mark_broadcast_completed(self, item: Broadcast) -> None:
        item.status = "completed"
        item.completed_at = datetime.now(timezone.utc)
