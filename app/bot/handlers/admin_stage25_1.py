from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_stage25 import export_choice_keyboard
from app.bot.keyboards.admin_stage25_1 import (
    broadcast_audience_keyboard,
    referral_card_keyboard,
    referrals_keyboard,
)
from app.bot.states.marketing import BroadcastCreate
from app.core.admin_metrics import AdminMetricsRepository
from app.core.config import load_settings
from app.repositories.marketing import MarketingRepository
from app.services.admin_bi import AdminBIService
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
            "📊 Статистика\n\n"
            f"• Всего — {number(data.users_total)}\n"
            f"• Живые — {number(data.users_alive)}\n"
            f"• Мёртвые — {number(data.users_dead)}\n\n"
            "👤 Прирост\n\n"
            f"• За сегодня — {number(data.today)}\n"
            f"• За неделю — {number(data.week)}\n"
            f"• За месяц — {number(data.month)}\n"
            f"• За всё время — {number(data.all_time)}\n\n"
            "📈 Органический прирост\n\n"
            f"• За сегодня — {number(data.organic_today)}\n"
            f"• За неделю — {number(data.organic_week)}\n"
            f"• За месяц — {number(data.organic_month)}\n"
            f"• За всё время — {number(data.organic_all_time)}\n\n"
            f"💳 Активных карт — {number(data.active_cards)}"
        ),
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
    chart_data = await AdminBIService(session).profit()

    def row(title: str, item) -> str:
        return (
            f"• {title} — {money(item.revenue_kopecks)} ₽ "
            f"({money(item.partner_kopecks)} ₽) "
            f"+{number(item.trials)} триал"
        )

    await message.answer_photo(
        BufferedInputFile(
            revenue_chart(chart_data.points),
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


@router.callback_query(F.data.regexp(r"^adminm:source:\\d+$"))
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
        return

    source = await session.get(
        __import__(
            "app.models.marketing",
            fromlist=["TrafficSource"],
        ).TrafficSource,
        source_id,
    )
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
            "✍️ Отправьте текст рассылки."
        )
    await callback.answer()


@router.callback_query(F.data == "admin25:broadcast:cancel")
async def broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_text("✖️ Рассылка отменена")
    await callback.answer()
