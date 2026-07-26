from __future__ import annotations

from html import escape

from aiogram import Bot, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.repositories import UserRepository
from app.repositories.marketing import MarketingRepository
from app.services.crm_tracking import CrmTrackingService

router = Router(name="start_marketing")
TERMS_URL = "https://sms.evocloud.su/terms"


@router.message(CommandStart())
async def start_with_terms(
    message: Message,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.from_user is None:
        return

    user = await UserRepository(session).upsert_from_telegram(message.from_user)

    args = (message.text or "").split(maxsplit=1)
    payload = args[1].strip() if len(args) > 1 else ""

    # Персональная ссылка должна обрабатываться старым start-router,
    # который запускает сценарий отправки анонимного сообщения.
    if payload and not payload.startswith("src_"):
        raise SkipHandler

    source = None
    if payload.startswith("src_"):
        source = await MarketingRepository(session).source_by_code(
            payload.removeprefix("src_")
        )
        if source is not None:
            await MarketingRepository(session).register_source_start(
                source=source,
                user=user,
            )

    tracking = CrmTrackingService(session)
    await tracking.bot_started(user_id=user.id)
    if source is not None:
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
        "При использовании бота, вы автоматически соглашаетесь "
        f'с <a href="{TERMS_URL}">условиями пользования</a>.',
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await message.answer(
        "🔗 Ваша индивидуальная ссылка\n\n"
        f"<code>{escape(personal_link)}</code>\n\n"
        "Разместите её в профиле, канале или сторис.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
