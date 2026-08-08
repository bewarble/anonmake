from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.crm import CrmEvent, CrmNote, CrmTag, CrmUserTag
from app.models.marketing import SourceAttribution, TrafficSource
from app.models.user import User


@dataclass(slots=True, frozen=True)
class CrmProfile:
    tags: list[CrmTag]
    notes: list[CrmNote]
    events: list[CrmEvent]
    source: TrafficSource | None


class CrmRepository:
    def __init__(self, session: AsyncSession, *, bot_id: int | None = None) -> None:
        self.session = session
        self.bot_id = bot_id

    def _bot_id(self) -> int:
        return self.bot_id if self.bot_id is not None else require_current_bot().id

    async def _require_user(self, user_id: int) -> User:
        bot_id = self._bot_id()
        user = await self.session.scalar(
            select(User).where(User.id == user_id, User.bot_id == bot_id)
        )
        if user is None:
            raise ValueError("CRM user does not belong to the current bot")
        return user

    async def profile(self, user_id: int) -> CrmProfile:
        user = await self._require_user(user_id)
        tags = list(
            (
                await self.session.execute(
                    select(CrmTag)
                    .join(CrmUserTag, CrmUserTag.tag_id == CrmTag.id)
                    .where(CrmUserTag.user_id == user.id)
                    .order_by(CrmTag.name)
                )
            ).scalars()
        )
        notes = list(
            (
                await self.session.execute(
                    select(CrmNote)
                    .where(CrmNote.user_id == user.id)
                    .order_by(CrmNote.id.desc())
                    .limit(5)
                )
            ).scalars()
        )
        events = list(
            (
                await self.session.execute(
                    select(CrmEvent)
                    .where(CrmEvent.user_id == user.id)
                    .order_by(CrmEvent.occurred_at.desc(), CrmEvent.id.desc())
                    .limit(12)
                )
            ).scalars()
        )
        source = await self.session.scalar(
            select(TrafficSource)
            .join(
                SourceAttribution,
                SourceAttribution.source_id == TrafficSource.id,
            )
            .where(
                SourceAttribution.user_id == user.id,
                TrafficSource.bot_id == user.bot_id,
            )
        )
        return CrmProfile(tags=tags, notes=notes, events=events, source=source)

    async def add_note(
        self,
        *,
        user_id: int,
        text: str,
        admin_telegram_id: int,
    ) -> CrmNote:
        user = await self._require_user(user_id)
        note = CrmNote(
            user_id=user.id,
            text=text,
            created_by_telegram_id=admin_telegram_id,
        )
        self.session.add(note)
        await self.session.flush()
        return note

    async def ensure_tag(
        self,
        *,
        name: str,
        admin_telegram_id: int,
    ) -> CrmTag:
        normalized = " ".join(name.strip().split())[:48]
        existing = await self.session.scalar(
            select(CrmTag).where(CrmTag.name == normalized)
        )
        if existing is not None:
            return existing
        tag = CrmTag(
            name=normalized,
            created_by_telegram_id=admin_telegram_id,
        )
        self.session.add(tag)
        await self.session.flush()
        return tag

    async def assign_tag(
        self,
        *,
        user_id: int,
        tag: CrmTag,
        admin_telegram_id: int,
    ) -> bool:
        user = await self._require_user(user_id)
        existing = await self.session.scalar(
            select(CrmUserTag).where(
                CrmUserTag.user_id == user.id,
                CrmUserTag.tag_id == tag.id,
            )
        )
        if existing is not None:
            return False
        self.session.add(
            CrmUserTag(
                user_id=user.id,
                tag_id=tag.id,
                assigned_by_telegram_id=admin_telegram_id,
            )
        )
        await self.session.flush()
        return True

    async def remove_tag(self, *, user_id: int, tag_id: int) -> bool:
        user = await self._require_user(user_id)
        result = await self.session.execute(
            delete(CrmUserTag).where(
                CrmUserTag.user_id == user.id,
                CrmUserTag.tag_id == tag_id,
            )
        )
        return bool(result.rowcount)

    async def record_event(
        self,
        *,
        user_id: int,
        event_type: str,
        summary: str,
        external_key: str | None = None,
    ) -> CrmEvent | None:
        user = await self._require_user(user_id)
        if external_key:
            # The database constraint is globally unique. Ownership is already
            # validated above; keep the dedupe lookup global so a duplicated key
            # remains idempotent instead of surfacing as an IntegrityError.
            existing = await self.session.scalar(
                select(CrmEvent).where(CrmEvent.external_key == external_key)
            )
            if existing is not None:
                return None
        item = CrmEvent(
            user_id=user.id,
            event_type=event_type,
            summary=summary[:500],
            external_key=external_key,
        )
        self.session.add(item)
        await self.session.flush()
        return item
