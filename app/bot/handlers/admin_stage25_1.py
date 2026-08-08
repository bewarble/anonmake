from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_stage25_1 import (
    broadcast_audience_keyboard,
    export_choice_keyboard,
    referral_card_keyboard,
    referrals_keyboard,
)
from app.bot.ui import (
    ADMIN_BROADCAST,
    ADMIN_EXPORT,
    ADMIN_PROFIT,
    ADMIN_SOURCES,
    ADMIN_STATISTICS,
)
from app.bot.states.marketing import BroadcastCreate
from app.bot.keyboards.marketing import broadcast_text_cancel_keyboard
from app.core.admin_metrics import AdminMetricsRepository
from app.core import admin_texts
from app.core.config import load_settings
from app.models.marketing import TrafficSource
from app.repositories.marketing import MarketingRepository
from app.services.admin_charts_stage25 import revenue_chart, statistics_chart
from app.services.admin_statistics_stage25 import AdminStatisticsStage25Repository

router = Router(name="admin_stage25_1")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


def number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


async def delete_message_quietly(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except Exception:
        return


def source_list_text(count: int) -> str:
    if count:
        return "🔗 <b>Реферальные ссылки</b>\n\nВыберите источник, чтобы открыть статистику."
    return "🔗 <b>Реферальные ссылки</b>\n\nИсточников пока нет. Создайте первую реферальную ссылку."


@router.message(F.text.in_({ADMIN_STATISTICS, "Статистика"}))
async def statistics(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    data = await AdminStatisticsStage25Repository(session).snapshot()
    await delete_message_quietly(message)
    await message.answer_photo(
        BufferedInputFile(statistics_chart(data.points), filename="statistics.png"),
        caption=(
            "📊 <b>Статистика</b>\n\n"
            "👥 <b>Пользователи</b>\n"
            f"• Всего — {number(data.users_total)}\n"
            f"• Живые — {number(data.users_alive)}\n"
            f"• Мертвые — {number(data.users_dead)}\n\n"
            "📈 <b>Прирост</b>\n"
            f"• За сегодня — {number(data.today)}\n"
            f"• За неделю — {number(data.week)}\n"
            f"• За месяц — {number(data.month)}\n\n"
            "♻️ <b>Саморост</b>\n"
            f"• За сегодня — {number(data.organic_today)}\n"
            f"• За неделю — {number(data.organic_week)}\n"
            f"• За месяц — {number(data.organic_month)}\n\n"
            f"⚡️ Всего карт: {number(data.total_cards)}\n"
            f"💳 Активные карты: {number(data.active_cards)}"
        ),
        parse_mode="HTML",
    )


@router.message(F.text.in_({ADMIN_PROFIT, "Прибыль"}))
async def profit(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    settings = load_settings()
    trial_kinds = tuple(value.strip() for value in settings.trial_attempt_kinds.split(",") if value.strip())
    metrics = await AdminMetricsRepository(session).profit(trial_kinds)
    revenue_points = await AdminMetricsRepository(session).daily_revenue()

    def row(title: str, item) -> str:
        return f"• {title} — {money(item.revenue_kopecks)} ₽ ({money(item.partner_kopecks)} ₽) +{number(item.trials)} пдп"

    await delete_message_quietly(message)
    await message.answer_photo(
        BufferedInputFile(revenue_chart(revenue_points), filename="revenue.png"),
        caption=(
            "💰 Прибыль\n\n"
            f"{row('За сегодня', metrics.today)}\n"
            f"{row('За неделю', metrics.week)}\n"
            f"{row('За месяц', metrics.month)}\n\n"
            f"{row('За всё время', metrics.all_time)}"
        ),
    )


@router.message(F.text.in_({ADMIN_EXPORT, "Выгрузка"}))
async def export_prompt(message: Message) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    await delete_message_quietly(message)
    await message.answer(admin_texts.EXPORT_PROMPT, reply_markup=export_choice_keyboard())


@router.callback_query(F.data.startswith("admin25:export:"))
async def export_users(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    mode = (callback.data or "").rsplit(":", 1)[-1]
    if mode not in {"all", "alive"}:
        await callback.answer(admin_texts.INVALID_DATA, show_alert=True)
        return
    alive_only = mode == "alive"
    payload = await AdminMetricsRepository(session).export_user_ids(alive_only=alive_only)
    filename = "anonmake-users-alive.txt" if alive_only else "anonmake-users-all.txt"
    title = admin_texts.EXPORT_READY_ALIVE if alive_only else admin_texts.EXPORT_READY_ALL
    if callback.message:
        await delete_message_quietly(callback.message)
        await callback.message.answer_document(BufferedInputFile(payload, filename=filename), caption=title)
    await callback.answer()


@router.message(F.text.in_({ADMIN_SOURCES, "Источники"}))
async def referrals(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    sources = await MarketingRepository(session).sources()
    await delete_message_quietly(message)
    await message.answer(
        source_list_text(len(sources)),
        parse_mode="HTML",
        reply_markup=referrals_keyboard(sources, page=0),
    )


@router.callback_query(F.data == "admin25:referrals")
async def referrals_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    sources = await MarketingRepository(session).sources()
    if callback.message:
        await delete_message_quietly(callback.message)
        await callback.message.answer(
            source_list_text(len(sources)),
            parse_mode="HTML",
            reply_markup=referrals_keyboard(sources, page=0),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin25:referrals:page:"))
async def referrals_page(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    try:
        page = max(int((callback.data or "").rsplit(":", 1)[1]), 0)
    except ValueError:
        page = 0
    sources = await MarketingRepository(session).sources()
    if callback.message:
        await callback.message.edit_text(
            source_list_text(len(sources)),
            parse_mode="HTML",
            reply_markup=referrals_keyboard(sources, page=page),
        )
    await callback.answer()


@router.callback_query(F.data == "admin25:referrals:noop")
async def referrals_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.regexp(r"^adminm:source:\d+$"))
async def referral_details(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    try:
        source_id = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer(admin_texts.INVALID_DATA, show_alert=True)
        return
    source = await session.get(TrafficSource, source_id)
    stats = await MarketingRepository(session).source_stats(source_id)
    if source is None or stats is None:
        await callback.answer(admin_texts.SOURCE_NOT_FOUND, show_alert=True)
        return
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=src_{source.code}"
    clicks = int(stats["clicks"])
    attributed = int(stats["attributed"])
    cpc = "Н/д" if not clicks else money(int(stats["cpc_kopecks"]))
    cpu = "Н/д" if not attributed else money(int(stats["cpa_kopecks"]))
    text = (
        f"Название ссылки: <b>{escape(source.name)}</b>\n\n"
        "📊 <b>Статистика:</b>\n"
        f"• Всего перешли — {number(clicks)}\n"
        f"• Из них уникальны — {number(attributed)}\n"
        f"• Из них живы — {number(int(stats['alive']))}\n\n"
        "👤 <b>Статистика по времени:</b>\n"
        f"• Сегодня — {number(int(stats['today']))}\n"
        f"• За последние 7 дней — {number(int(stats['week']))}\n"
        f"• За последние 31 день — {number(int(stats['month']))}\n\n"
        "💰 <b>Цены:</b>\n"
        f"• Цена ссылки — {money(int(stats['spend_kopecks']))} ₽\n"
        f"• Цена за переход — {cpc}{' ₽' if cpc != 'Н/д' else ''}\n"
        f"• Цена за уникального — {cpu}{' ₽' if cpu != 'Н/д' else ''}\n\n"
        f"Ссылка: {escape(link)}\n\n"
        f"⚡️ Всего карт: {number(int(stats['total_cards']))}\n"
        f"💳 Активных карт: {number(int(stats['active_cards']))}"
    )
    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=referral_card_keyboard(source.id),
            disable_web_page_preview=True,
        )
    await callback.answer()


@router.message(F.text.in_({ADMIN_BROADCAST, "Рассылка"}))
async def broadcast_start(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(BroadcastCreate.waiting_audience)
    await delete_message_quietly(message)
    await message.answer(admin_texts.BROADCAST_AUDIENCE_PROMPT, reply_markup=broadcast_audience_keyboard())


@router.callback_query(F.data.startswith("admin25:broadcast:audience:"))
async def broadcast_audience(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    audience = (callback.data or "").rsplit(":", 1)[1]
    if audience not in {"all", "vip", "non_vip"}:
        await callback.answer(admin_texts.INVALID_DATA, show_alert=True)
        return
    await state.update_data(kind="anonymous", audience=audience)
    await state.set_state(BroadcastCreate.waiting_text)
    if callback.message:
        await delete_message_quietly(callback.message)
        prompt = await callback.message.answer(
            admin_texts.BROADCAST_TEXT_PROMPT,
            reply_markup=broadcast_text_cancel_keyboard(),
        )
        await state.update_data(text_prompt_message_id=prompt.message_id)
    await callback.answer()


@router.message(BroadcastCreate.waiting_text, Command("cancel"))
async def broadcast_text_cancel_command(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    await state.clear()
    await delete_message_quietly(message)


@router.callback_query(F.data == "admin25:broadcast:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    await state.clear()
    if callback.message:
        await delete_message_quietly(callback.message)
    await callback.answer()
