from __future__ import annotations

from html import escape
from urllib.parse import urlparse

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.source_admin import cancel_source_keyboard, source_card_keyboard
from app.bot.keyboards.admin_stage25 import referral_back_keyboard
from app.bot.keyboards.marketing import (
    audience_keyboard,
    broadcast_confirm_keyboard,
    broadcasts_menu,
    source_list_keyboard,
    sources_menu,
)
from app.bot.states.marketing import BroadcastCreate, SourceCreate
from app.core.config import load_settings
from app.repositories.admin import AdminRepository
from app.repositories.marketing import MarketingRepository

router = Router(name="admin_marketing")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


@router.callback_query(F.data == "adminm:sources")
async def sources_home(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    items = await MarketingRepository(session).sources()
    text = "📣 Источники\n\nРекламные ссылки и статистика прихода."
    if callback.message:
        await callback.message.edit_text(
            text,
            reply_markup=source_list_keyboard(items),
        )
    await callback.answer()


@router.callback_query(F.data == "adminm:source:create")
async def source_create_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    await state.set_state(SourceCreate.waiting_name)
    if callback.message:
        await callback.message.answer("Название источника:", reply_markup=cancel_source_keyboard())
    await callback.answer()


@router.message(SourceCreate.waiting_name)
async def source_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Укажите название")
        return
    await state.update_data(name=name)
    await state.set_state(SourceCreate.waiting_url)
    await message.answer("Ссылка на источник рекламы:", reply_markup=cancel_source_keyboard())


@router.message(SourceCreate.waiting_url)
async def source_url(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        await message.answer("Укажите корректную http/https ссылку")
        return
    await state.update_data(source_url=value)
    await state.set_state(SourceCreate.waiting_spend)
    await message.answer("Сумма закупа в рублях, например 15000:", reply_markup=cancel_source_keyboard())


@router.message(SourceCreate.waiting_spend)
async def source_spend(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    raw = (message.text or "").replace(" ", "").replace(",", ".")
    try:
        rubles = float(raw)
    except ValueError:
        await message.answer("Введите сумму числом")
        return
    if rubles < 0:
        await message.answer("Сумма не может быть отрицательной")
        return

    data = await state.get_data()
    source = await MarketingRepository(session).create_source(
        name=data["name"],
        source_url=data["source_url"],
        spend_kopecks=round(rubles * 100),
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
        "✅ Источник создан\n\n"
        f"Название: {escape(source.name)}\n"
        f"Рекламная ссылка:\n<code>{escape(link)}</code>",
        parse_mode="HTML",
        reply_markup=referral_back_keyboard(),
    )


@router.callback_query(F.data.startswith("adminm:source:"))
async def source_details(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    try:
        source_id = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    source = await session.get(__import__(
        "app.models.marketing", fromlist=["TrafficSource"]
    ).TrafficSource, source_id)
    stats = await MarketingRepository(session).source_stats(source_id)
    if source is None or stats is None:
        await callback.answer("Источник не найден", show_alert=True)
        return

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=src_{source.code}"
    attributed = stats["attributed"]
    cpa = (
        stats["spend_kopecks"] / attributed / 100
        if attributed
        else 0
    )
    text = (
        f"📣 {escape(source.name)}\n\n"
        f"Источник: {escape(source.source_url)}\n"
        f"Закуп: {stats['spend_kopecks'] / 100:.2f} ₽\n"
        f"Переходы: {stats['clicks']}\n"
        f"Новые пользователи: {attributed}\n"
        f"Цена пользователя: {cpa:.2f} ₽\n\n"
        f"<code>{escape(link)}</code>"
    )
    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=source_card_keyboard(source.id),
        )
    await callback.answer()


@router.callback_query(F.data == "adminm:broadcasts")
async def broadcasts_home(callback: CallbackQuery) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return
    if callback.message:
        await callback.message.edit_text(
            "📢 Рассылки\n\nВыберите тип сообщения.",
            reply_markup=broadcasts_menu(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adminm:broadcast:kind:"))
async def broadcast_kind(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    kind = (callback.data or "").rsplit(":", 1)[1]
    await state.update_data(kind=kind)
    await state.set_state(BroadcastCreate.waiting_audience)
    if callback.message:
        await callback.message.edit_text(
            "Выберите аудиторию:",
            reply_markup=audience_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adminm:broadcast:audience:"))
async def broadcast_audience(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    audience = (callback.data or "").rsplit(":", 1)[1]
    await state.update_data(audience=audience)
    await state.set_state(BroadcastCreate.waiting_text)
    if callback.message:
        await callback.message.answer("Отправьте текст рассылки:")
    await callback.answer()


@router.message(BroadcastCreate.waiting_text)
async def broadcast_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не может быть пустым")
        return
    if len(text) > 4000:
        await message.answer("Максимум 4000 символов")
        return

    await state.update_data(text=text)
    await state.set_state(BroadcastCreate.waiting_confirm)
    await message.answer(
        "Предпросмотр:\n\n" + text,
        reply_markup=broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data == "adminm:broadcast:confirm")
async def broadcast_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    data = await state.get_data()
    item = await MarketingRepository(session).create_broadcast(
        kind=data["kind"],
        audience=data["audience"],
        text=data["text"],
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
            f"✅ Рассылка #{item.id} поставлена в очередь"
        )
    await callback.answer()


@router.callback_query(F.data == "adminm:broadcast:cancel")
async def broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Рассылка отменена")
    await callback.answer()
