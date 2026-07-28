from __future__ import annotations

from datetime import datetime, timezone
import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import get_current_bot
from app.models.bot_instance import BotInstance
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
        clicks = int(source.clicks or 0)
        cpa_kopecks = (
            round(source.spend_kopecks / attributed)
            if attributed
            else 0
        )
        conversion_percent = (
            attributed / clicks * 100
            if clicks
            else 0.0
        )
        return {
            "clicks": clicks,
            "attributed": attributed,
            "spend_kopecks": source.spend_kopecks,
            "cpa_kopecks": cpa_kopecks,
            "conversion_percent": conversion_percent,
        }

    async def sources_summary(self) -> dict[str, int]:
        source_ids = select(TrafficSource.id).where(
            TrafficSource.is_active.is_(True)
        )
        spend_kopecks = int(
            await self.session.scalar(
                select(func.coalesce(func.sum(TrafficSource.spend_kopecks), 0))
                .where(TrafficSource.is_active.is_(True))
            )
            or 0
        )
        attributed = int(
            await self.session.scalar(
                select(func.count(SourceAttribution.id)).where(
                    SourceAttribution.source_id.in_(source_ids)
                )
            )
            or 0
        )
        average_cpa_kopecks = (
            round(spend_kopecks / attributed)
            if attributed
            else 0
        )
        return {
            "spend_kopecks": spend_kopecks,
            "attributed": attributed,
            "average_cpa_kopecks": average_cpa_kopecks,
        }

    async def create_broadcast(
        self,
        *,
        kind: str,
        audience: str,
        text: str,
        admin_telegram_id: int,
        bot_id: int | None = None,
    ) -> Broadcast:
        if kind != "anonymous":
            raise ValueError("Unsupported broadcast kind")
        if audience not in {"all", "vip", "non_vip"}:
            raise ValueError("Unsupported broadcast audience")
        if not text.strip() or len(text) > 4000:
            raise ValueError("Invalid broadcast text")

        resolved_bot_id = bot_id
        if resolved_bot_id is None:
            current_bot = get_current_bot()
            if current_bot is not None:
                resolved_bot_id = current_bot.id
            else:
                resolved_bot_id = await self.session.scalar(
                    select(BotInstance.id)
                    .where(BotInstance.is_active.is_(True))
                    .order_by(BotInstance.id)
                    .limit(1)
                )
        if resolved_bot_id is None:
            raise RuntimeError("No active bot instance is available")

        item = Broadcast(
            bot_id=resolved_bot_id,
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


    async def broadcast_audience_count(self, audience: str) -> int:
        from datetime import datetime, timezone
        from sqlalchemy import exists
        from app.models.billing import Subscription
        from app.models.user import User

        query = select(func.count(User.id))
        now = datetime.now(timezone.utc)
        active_access = exists(
            select(Subscription.id).where(
                Subscription.user_id == User.id,
                Subscription.access_until.is_not(None),
                Subscription.access_until > now,
            )
        )
        if audience == "vip":
            query = query.where(active_access)
        elif audience == "non_vip":
            query = query.where(~active_access)
        return int(await self.session.scalar(query) or 0)

    async def broadcast_delivery_stats(self, broadcast_id: int) -> dict[str, int]:
        from app.models.delivery import DeliveryOutbox

        item = await self.session.get(Broadcast, broadcast_id)
        if item is None:
            return {"delivered": 0, "failed": 0, "pending": 0, "blocked": 0}

        prefix = f"broadcast:{broadcast_id}:user:%"
        rows = await self.session.execute(
            select(
                DeliveryOutbox.status,
                func.count(DeliveryOutbox.id),
            )
            .where(
                DeliveryOutbox.bot_id == item.bot_id,
                DeliveryOutbox.dedupe_key.like(prefix),
            )
            .group_by(DeliveryOutbox.status)
        )
        values = {status: int(count) for status, count in rows}
        delivered = values.get("delivered", 0)
        failed = values.get("failed", 0)
        pending = sum(
            values.get(status, 0)
            for status in ("pending", "retry", "processing")
        )
        blocked = int(
            await self.session.scalar(
                select(func.count(DeliveryOutbox.id)).where(
                    DeliveryOutbox.bot_id == item.bot_id,
                    DeliveryOutbox.dedupe_key.like(prefix),
                    DeliveryOutbox.status == "failed",
                    func.lower(DeliveryOutbox.last_error).like("%blocked%"),
                )
            )
            or 0
        )
        return {
            "delivered": delivered,
            "failed": failed,
            "pending": pending,
            "blocked": blocked,
        }

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
