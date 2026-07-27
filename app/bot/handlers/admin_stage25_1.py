from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_stage25_1 import (
    broadcast_audience_keyboard,
    export_choice_keyboard,
    referral_card_keyboard,
    referrals_keyboard,
)
from app.bot.states.marketing import BroadcastCreate
from app.bot.keyboards.marketing import broadcast_text_cancel_keyboard
from app.core.admin_metrics import AdminMetricsRepository
from app.core.config import load_settings
from app.models.marketing import TrafficSource
from app.repositories.marketing import MarketingRepository
from app.services.admin_charts_stage25 import revenue_chart, statistics_chart
from app.services.admin_statistics_stage25 import (
    AdminStatisticsStage25Repository,
)

router = Router(name="admin_stage25_1")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


def number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


@router.message(F.text == "Статистика")
async def statistics(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    data = await AdminStatisticsStage25Repository(session).snapshot()

    await message.answer_photo(
        BufferedInputFile(
            statistics_chart(data.points),
            filename="statistics.png",
        ),
        caption=(
            "📊 <b>Общая статистика</b>\n\n"
            "📁 <b>Статистика:</b>\n"
            f"• Всего — {number(data.users_total)}\n"
            f"• Живые — {number(data.users_alive)}\n"
            f"• Мёртвые — {number(data.users_dead)}\n\n"
            "👤 <b>Прирост:</b>\n"
            f"• За сегодня — {number(data.today)}\n"
            f"• За неделю — {number(data.week)}\n"
            f"• За месяц — {number(data.month)}\n\n"
            "📈 <b>Саморост:</b>\n"
            f"• За сегодня — {number(data.organic_today)}\n"
            f"• За неделю — {number(data.organic_week)}\n"
            f"• За месяц — {number(data.organic_month)}\n\n"
            f"💳 Активных карт — {number(data.active_cards)}"
        ),
        parse_mode="HTML",
    )


@router.message(F.text == "Прибыль")
async def profit(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    settings = load_settings()
    trial_kinds = tuple(
        value.strip()
        for value in settings.trial_attempt_kinds.split(",")
        if value.strip()
    )

    metrics = await AdminMetricsRepository(session).profit(trial_kinds)
    revenue_points = await AdminMetricsRepository(session).daily_revenue()

    def row(title: str, item) -> str:
        return (
            f"• {title} — {money(item.revenue_kopecks)} ₽ "
            f"({money(item.partner_kopecks)} ₽)\n"
            f"+{number(item.trials)} новых подписок"
        )

    await message.answer_photo(
        BufferedInputFile(
            revenue_chart(revenue_points),
            filename="revenue.png",
        ),
        caption=(
            "💰 Прибыль\n\n"
            f"{row('За сегодня', metrics.today)}\n"
            f"{row('За неделю', metrics.week)}\n"
            f"{row('За месяц', metrics.month)}\n\n"
            f"{row('За всё время', metrics.all_time)}"
        ),
    )


@router.message(F.text == "Выгрузка")
async def export_prompt(message: Message) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    await message.answer(
        "📄 Выгрузка\n\nКого выгрузить?",
        reply_markup=export_choice_keyboard(),
    )


@router.callback_query(F.data.startswith("admin25:export:"))
async def export_users(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    mode = (callback.data or "").rsplit(":", 1)[-1]
    if mode not in {"all", "alive"}:
        await callback.answer(
            "Некорректный режим выгрузки",
            show_alert=True,
        )
        return

    alive_only = mode == "alive"

    payload = await AdminMetricsRepository(session).export_user_ids(
        alive_only=alive_only,
    )

    filename = (
        "anonmake-users-alive.txt"
        if alive_only
        else "anonmake-users-all.txt"
    )

    title = (
        "✅ Выгрузка живых пользователей готова"
        if alive_only
        else "✅ Выгрузка всех пользователей готова"
    )

    if callback.message:
        await callback.message.answer_document(
            BufferedInputFile(
                payload,
                filename=filename,
            ),
            caption=title,
        )

    await callback.answer()


@router.message(F.text == "Рефералы")
async def referrals(
    message: Message,
    session: AsyncSession,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    sources = await MarketingRepository(session).sources()
    await message.answer(
        (
            "📣 Рефералы\n\n"
            f"Источников: {number(len(sources))}\n"
            "Выберите источник или создайте новый."
        ),
        reply_markup=referrals_keyboard(sources),
    )


@router.callback_query(F.data == "admin25:referrals")
async def referrals_callback(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    sources = await MarketingRepository(session).sources()
    if callback.message:
        await callback.message.edit_text(
            (
                "📣 Рефералы\n\n"
                f"Источников: {number(len(sources))}\n"
                "Выберите источник или создайте новый."
            ),
            reply_markup=referrals_keyboard(sources),
        )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^adminm:source:\d+$"))
async def referral_details(
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

    source = await session.get(TrafficSource, source_id)
    stats = await MarketingRepository(session).source_stats(source_id)

    if source is None or stats is None:
        await callback.answer("Источник не найден", show_alert=True)
        return

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=src_{source.code}"
    attributed = int(stats["attributed"])
    cpa = (
        int(stats["spend_kopecks"]) / attributed / 100
        if attributed
        else 0
    )

    if callback.message:
        await callback.message.edit_text(
            (
                f"📣 {escape(source.name)}\n\n"
                f"Закуп: {int(stats['spend_kopecks']) / 100:.2f} ₽\n"
                f"Переходы: {int(stats['clicks'])}\n"
                f"Пользователи: {attributed}\n"
                f"Цена пользователя: {cpa:.2f} ₽\n\n"
                f"<code>{escape(link)}</code>"
            ),
            parse_mode="HTML",
            reply_markup=referral_card_keyboard(source.id),
        )
    await callback.answer()


@router.message(F.text == "Рассылка")
async def broadcast_start(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    await state.clear()
    await state.set_state(BroadcastCreate.waiting_audience)
    await message.answer(
        "📢 Рассылка\n\nКому отправить сообщение?",
        reply_markup=broadcast_audience_keyboard(),
    )


@router.callback_query(F.data.startswith("admin25:broadcast:audience:"))
async def broadcast_audience(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    audience = (callback.data or "").rsplit(":", 1)[1]
    if audience not in {"all", "vip", "non_vip"}:
        await callback.answer("Некорректная аудитория", show_alert=True)
        return

    await state.update_data(
        kind="anonymous",
        audience=audience,
    )
    await state.set_state(BroadcastCreate.waiting_text)

    if callback.message:
        await callback.message.answer(
            "✍️ Отправьте текст рассылки.\n\n"
            "Для отмены нажмите кнопку ниже или отправьте /cancel.",
            reply_markup=broadcast_text_cancel_keyboard(),
        )
    await callback.answer()



@router.message(BroadcastCreate.waiting_text, Command("cancel"))
async def broadcast_text_cancel_command(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    await state.clear()
    await message.answer("✖️ Рассылка отменена")


@router.callback_query(F.data == "admin25:broadcast:cancel")
async def broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    await state.clear()
    if callback.message:
        await callback.message.edit_text("✖️ Рассылка отменена")
    await callback.answer()
