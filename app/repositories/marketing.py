from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.billing import PaymentMethod, Subscription
from app.models.delivery import DeliveryOutbox
from app.models.marketing import Broadcast, SourceAttribution, SourceClick, TrafficSource
from app.models.user import User


class MarketingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_source(self, *, name: str, source_url: str, spend_kopecks: int, admin_telegram_id: int) -> TrafficSource:
        current_bot = require_current_bot()
        source = TrafficSource(bot_id=current_bot.id, name=name, code=secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12], source_url=source_url, spend_kopecks=spend_kopecks, created_by_telegram_id=admin_telegram_id)
        self.session.add(source)
        await self.session.flush()
        return source

    async def source_by_code(self, code: str) -> TrafficSource | None:
        return await self.session.scalar(select(TrafficSource).where(TrafficSource.bot_id == require_current_bot().id, TrafficSource.code == code, TrafficSource.is_active.is_(True)))

    async def record_source_click(self, source: TrafficSource, user: User) -> bool:
        bot_id = require_current_bot().id
        if source.bot_id != bot_id or user.bot_id != bot_id:
            raise ValueError("Source click entities must belong to the current bot")
        click = SourceClick(source_id=source.id, user_id=user.id)
        try:
            async with self.session.begin_nested():
                self.session.add(click)
                await self.session.flush()
        except IntegrityError:
            return False
        source.clicks = int(source.clicks or 0) + 1
        await self.session.flush()
        return True

    async def register_source_start(self, *, source: TrafficSource, user: User) -> bool:
        bot_id = require_current_bot().id
        if source.bot_id != bot_id or user.bot_id != bot_id:
            raise ValueError("Source attribution entities must belong to the current bot")
        existing = await self.session.scalar(select(SourceAttribution.id).where(SourceAttribution.user_id == user.id))
        if existing is not None:
            return False
        attribution = SourceAttribution(source_id=source.id, user_id=user.id)
        try:
            async with self.session.begin_nested():
                self.session.add(attribution)
                await self.session.flush()
        except IntegrityError:
            return False
        return True

    async def sources(self, limit: int = 200) -> list[TrafficSource]:
        result = await self.session.execute(select(TrafficSource).where(TrafficSource.bot_id == require_current_bot().id, TrafficSource.is_active.is_(True)).order_by(TrafficSource.id.desc()).limit(limit))
        return list(result.scalars())

    async def source_stats(self, source_id: int) -> dict[str, int | float] | None:
        bot_id = require_current_bot().id
        source = await self.session.scalar(select(TrafficSource).where(TrafficSource.id == source_id, TrafficSource.bot_id == bot_id))
        if source is None:
            return None
        now = datetime.now(timezone.utc)
        attributed_users = select(SourceAttribution.user_id).join(User, User.id == SourceAttribution.user_id).where(SourceAttribution.source_id == source.id, User.bot_id == bot_id)
        attributed = int(await self.session.scalar(select(func.count(SourceAttribution.id)).where(SourceAttribution.source_id == source.id)) or 0)
        alive = int(await self.session.scalar(select(func.count(User.id)).where(User.id.in_(attributed_users), User.bot_id == bot_id, User.is_blocked.is_(False))) or 0)

        async def since(days: int) -> int:
            left = now - timedelta(days=days)
            return int(await self.session.scalar(select(func.count(SourceAttribution.id)).where(SourceAttribution.source_id == source.id, SourceAttribution.first_seen_at >= left)) or 0)

        total_cards = int(await self.session.scalar(select(func.count(func.distinct(PaymentMethod.user_id))).where(PaymentMethod.bot_id == bot_id, PaymentMethod.user_id.in_(attributed_users), PaymentMethod.binding_id.is_not(None))) or 0)
        active_cards = int(await self.session.scalar(select(func.count(func.distinct(PaymentMethod.user_id))).join(Subscription, (Subscription.bot_id == PaymentMethod.bot_id) & (Subscription.user_id == PaymentMethod.user_id)).where(PaymentMethod.bot_id == bot_id, PaymentMethod.user_id.in_(attributed_users), PaymentMethod.binding_id.is_not(None), Subscription.auto_renew.is_(True))) or 0)
        clicks = int(source.clicks or 0)
        cpc_kopecks = round(source.spend_kopecks / clicks) if clicks else 0
        cpu_kopecks = round(source.spend_kopecks / attributed) if attributed else 0
        return {"clicks": clicks, "attributed": attributed, "alive": alive, "today": await since(1), "week": await since(7), "month": await since(31), "spend_kopecks": source.spend_kopecks, "cpc_kopecks": cpc_kopecks, "cpa_kopecks": cpu_kopecks, "total_cards": total_cards, "active_cards": active_cards, "conversion_percent": attributed / clicks * 100 if clicks else 0.0}

    async def sources_summary(self) -> dict[str, int]:
        bot_id = require_current_bot().id
        source_ids = select(TrafficSource.id).where(TrafficSource.bot_id == bot_id, TrafficSource.is_active.is_(True))
        spend_kopecks = int(await self.session.scalar(select(func.coalesce(func.sum(TrafficSource.spend_kopecks), 0)).where(TrafficSource.bot_id == bot_id, TrafficSource.is_active.is_(True))) or 0)
        attributed = int(await self.session.scalar(select(func.count(SourceAttribution.id)).where(SourceAttribution.source_id.in_(source_ids))) or 0)
        average_cpa_kopecks = round(spend_kopecks / attributed) if attributed else 0
        return {"spend_kopecks": spend_kopecks, "attributed": attributed, "average_cpa_kopecks": average_cpa_kopecks}

    async def create_broadcast(self, *, kind: str, audience: str, text: str, admin_telegram_id: int, bot_id: int | None = None) -> Broadcast:
        if kind != "anonymous":
            raise ValueError("Unsupported broadcast kind")
        if audience not in {"all", "vip", "non_vip"}:
            raise ValueError("Unsupported broadcast audience")
        if not text.strip() or len(text) > 4000:
            raise ValueError("Invalid broadcast text")
        current_bot_id = require_current_bot().id
        if bot_id is not None and bot_id != current_bot_id:
            raise ValueError("Broadcast must belong to the current bot")
        item = Broadcast(bot_id=current_bot_id, kind=kind, audience=audience, text=text, status="queued", created_by_telegram_id=admin_telegram_id)
        self.session.add(item)
        await self.session.flush()
        return item

    async def recent_broadcasts(self, limit: int = 10) -> list[Broadcast]:
        result = await self.session.execute(select(Broadcast).where(Broadcast.bot_id == require_current_bot().id).order_by(Broadcast.id.desc()).limit(limit))
        return list(result.scalars())

    async def broadcast_audience_count(self, audience: str) -> int:
        bot_id = require_current_bot().id
        query = select(func.count(User.id)).where(User.bot_id == bot_id)
        now = datetime.now(timezone.utc)
        active_access = exists(select(Subscription.id).where(Subscription.bot_id == bot_id, Subscription.user_id == User.id, Subscription.access_until.is_not(None), Subscription.access_until > now))
        if audience == "vip":
            query = query.where(active_access)
        elif audience == "non_vip":
            query = query.where(~active_access)
        return int(await self.session.scalar(query) or 0)

    async def broadcast_delivery_stats(self, broadcast_id: int) -> dict[str, int]:
        bot_id = require_current_bot().id
        item = await self.session.scalar(select(Broadcast).where(Broadcast.id == broadcast_id, Broadcast.bot_id == bot_id))
        if item is None:
            return {"delivered": 0, "failed": 0, "pending": 0, "blocked": 0}
        prefix = f"broadcast:{broadcast_id}:user:%"
        rows = await self.session.execute(select(DeliveryOutbox.status, func.count(DeliveryOutbox.id)).where(DeliveryOutbox.bot_id == item.bot_id, DeliveryOutbox.dedupe_key.like(prefix)).group_by(DeliveryOutbox.status))
        values = {status: int(count) for status, count in rows}
        delivered = values.get("delivered", 0)
        failed = values.get("failed", 0)
        pending = sum(values.get(status, 0) for status in ("pending", "retry", "processing"))
        blocked = int(await self.session.scalar(select(func.count(DeliveryOutbox.id)).where(DeliveryOutbox.bot_id == item.bot_id, DeliveryOutbox.dedupe_key.like(prefix), DeliveryOutbox.status == "failed", func.lower(DeliveryOutbox.last_error).like("%blocked%"))) or 0)
        return {"delivered": delivered, "failed": failed, "pending": pending, "blocked": blocked}

    async def next_broadcast(self) -> Broadcast | None:
        result = await self.session.execute(select(Broadcast).where(Broadcast.status.in_(("queued", "processing"))).order_by(Broadcast.id).limit(1).with_for_update(skip_locked=True))
        return result.scalar_one_or_none()

    async def mark_broadcast_started(self, item: Broadcast) -> None:
        if item.status == "queued":
            item.status = "processing"
            item.started_at = datetime.now(timezone.utc)

    async def mark_broadcast_completed(self, item: Broadcast) -> None:
        item.status = "completed"
        item.completed_at = datetime.now(timezone.utc)
