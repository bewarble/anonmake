from __future__ import annotations

from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import urlparse

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.source_admin import cancel_source_keyboard
from app.bot.keyboards.admin_stage25_1 import referral_back_keyboard
from app.bot.keyboards.marketing import (
    broadcast_preview_keyboard,
    broadcast_text_cancel_keyboard,
)
from app.bot.states.marketing import BroadcastCreate, SourceCreate
from app.core import texts, admin_texts
from app.core.config import load_settings
from app.repositories.admin import AdminRepository
from app.repositories.marketing import MarketingRepository

router = Router(name="admin_marketing")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


@router.callback_query(F.data == "adminm:source:create")
async def source_create_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return

    await state.set_state(SourceCreate.waiting_name)
    if callback.message:
        await callback.message.answer(
            admin_texts.SOURCE_NAME_PROMPT,
            reply_markup=cancel_source_keyboard(),
        )
    await callback.answer()


@router.message(SourceCreate.waiting_name)
async def source_name(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    name = " ".join((message.text or "").strip().split())
    if not name:
        await message.answer(admin_texts.SOURCE_NAME_EMPTY)
        return
    if len(name) > 120:
        await message.answer(admin_texts.SOURCE_NAME_LONG)
        return
    await state.update_data(name=name)
    await state.set_state(SourceCreate.waiting_url)
    await message.answer(
        admin_texts.SOURCE_URL_PROMPT,
        reply_markup=cancel_source_keyboard(),
    )


@router.message(SourceCreate.waiting_url)
async def source_url(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    value = (message.text or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        await message.answer(admin_texts.SOURCE_URL_INVALID)
        return
    if len(value) > 1000:
        await message.answer(admin_texts.SOURCE_URL_LONG)
        return
    await state.update_data(source_url=value)
    await state.set_state(SourceCreate.waiting_spend)
    await message.answer(
        admin_texts.SOURCE_SPEND_PROMPT,
        reply_markup=cancel_source_keyboard(),
    )


@router.message(SourceCreate.waiting_spend)
async def source_spend(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    raw = (message.text or "").replace(" ", "").replace(",", ".")
    try:
        rubles = Decimal(raw)
    except InvalidOperation:
        await message.answer(admin_texts.SOURCE_SPEND_INVALID)
        return
    if not rubles.is_finite() or rubles < 0:
        await message.answer(admin_texts.SOURCE_SPEND_INVALID)
        return
    if rubles > Decimal("1000000000"):
        await message.answer(admin_texts.SOURCE_SPEND_LARGE)
        return

    data = await state.get_data()
    name = data.get("name")
    source_url_value = data.get("source_url")
    if not isinstance(name, str) or not isinstance(source_url_value, str):
        await state.clear()
        await message.answer(admin_texts.SESSION_EXPIRED)
        return
    source = await MarketingRepository(session).create_source(
        name=name,
        source_url=source_url_value,
        spend_kopecks=int((rubles * 100).quantize(Decimal("1"))),
        admin_telegram_id=message.from_user.id,
    )
    await AdminRepository(session).audit(
        admin_telegram_id=message.from_user.id,
        action="create_traffic_source",
        target=str(source.id),
        details=f"name={source.name}",
    )
    await session.commit()
    await state.clear()

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=src_{source.code}"
    await message.answer(
        f"{admin_texts.SOURCE_CREATED}\n\n"
        f"Название: {escape(source.name)}\n"
        f"Рекламная ссылка:\n<code>{escape(link)}</code>",
        parse_mode="HTML",
        reply_markup=referral_back_keyboard(),
    )


@router.message(BroadcastCreate.waiting_text)
async def broadcast_text(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer(admin_texts.BROADCAST_TEXT_EMPTY)
        return
    if len(text) > 4000:
        await message.answer(admin_texts.BROADCAST_TEXT_LONG)
        return

    await state.update_data(text=text)
    await state.set_state(BroadcastCreate.waiting_confirm)
    await message.answer(
        texts.NEW_QUESTION.format(text=text),
        reply_markup=broadcast_preview_keyboard(),
    )



@router.callback_query(F.data == "adminm:broadcast:preview")
async def broadcast_preview_button(callback: CallbackQuery) -> None:
    await callback.answer(
        admin_texts.BROADCAST_PREVIEW_NOTE,
        show_alert=True,
    )


@router.callback_query(F.data == "adminm:broadcast:confirm")
async def broadcast_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return

    data = await state.get_data()
    kind = data.get("kind")
    audience = data.get("audience")
    text = data.get("text")
    if (
        kind != "anonymous"
        or audience not in {"all", "vip", "non_vip"}
        or not isinstance(text, str)
    ):
        await state.clear()
        await callback.answer(admin_texts.SESSION_EXPIRED, show_alert=True)
        return

    item = await MarketingRepository(session).create_broadcast(
        kind=kind,
        audience=audience,
        text=text,
        admin_telegram_id=callback.from_user.id,
    )
    await AdminRepository(session).audit(
        admin_telegram_id=callback.from_user.id,
        action="create_broadcast",
        target=str(item.id),
        details=f"kind={item.kind};audience={item.audience}",
    )
    await session.commit()
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            admin_texts.BROADCAST_QUEUED.format(item_id=item.id)
        )
    await callback.answer()


@router.callback_query(F.data == "adminm:broadcast:cancel")
async def broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return

    await state.clear()
    if callback.message:
        await callback.message.edit_text(admin_texts.BROADCAST_CANCELLED)
    await callback.answer()
