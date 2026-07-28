from __future__ import annotations

from aiogram import Bot, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.personal_link import personal_link_share_keyboard
from app.core import texts
from app.core.config import load_settings
from app.repositories import UserRepository
from app.repositories.marketing import MarketingRepository
from app.services.crm_tracking import CrmTrackingService

router = Router(name="start_marketing")

@router.message(CommandStart())
async def start_with_terms(
    message: Message,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.from_user is None:
        return

    args = (message.text or "").split(maxsplit=1)
    payload = args[1].strip() if len(args) > 1 else ""

    # Personal links are handled by the question flow. Do not mutate the
    # database before passing the update to the next router.
    if payload and not payload.startswith("src_"):
        raise SkipHandler

    user, is_new_user = await UserRepository(
        session
    ).get_or_create_from_telegram(message.from_user)

    source = None
    attributed = False
    if is_new_user and payload.startswith("src_"):
        source = await MarketingRepository(session).source_by_code(
            payload.removeprefix("src_")
        )
        if source is not None:
            attributed = await MarketingRepository(
                session
            ).register_source_start(
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

    me = await bot.get_me()
    personal_link = (
        f"https://t.me/{me.username}?start={user.public_code}"
    )

    await message.answer(
        f"{texts.PERSONAL_LINK.format(link=personal_link)}\n\n"
        f"{texts.PERSONAL_LINK_HINT}",
        reply_markup=personal_link_share_keyboard(personal_link),
    )
