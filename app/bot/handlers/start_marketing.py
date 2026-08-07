from __future__ import annotations

from aiogram import Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import UserRepository
from app.repositories.marketing import MarketingRepository
from app.services.crm_tracking import CrmTrackingService

router = Router(name="start_marketing")


@router.message(CommandStart())
async def track_start_source(
    message: Message,
    session: AsyncSession,
) -> None:
    """Record start/source analytics, then let the canonical start handler render UI."""
    if message.from_user is None:
        raise SkipHandler

    args = (message.text or "").split(maxsplit=1)
    payload = args[1].strip() if len(args) > 1 else ""

    user, is_new_user = await UserRepository(session).get_or_create_from_telegram(
        message.from_user
    )

    source = None
    attributed = False
    if payload.startswith("src_"):
        marketing = MarketingRepository(session)
        source = await marketing.source_by_code(payload.removeprefix("src_"))
        if source is not None:
            await marketing.record_source_click(source)
            if is_new_user:
                attributed = await marketing.register_source_start(
                    source=source,
                    user=user,
                )

    tracking = CrmTrackingService(session)
    await tracking.bot_started(user_id=user.id)
    if source is not None and attributed:
        await tracking.attributed_to_source(
            user_id=user.id,
            source_id=source.id,
            source_name=source.name,
        )

    await session.commit()

    raise SkipHandler
