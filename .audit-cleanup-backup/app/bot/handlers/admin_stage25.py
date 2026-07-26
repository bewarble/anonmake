from __future__ import annotations

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_stage25 import export_choice_keyboard
from app.core.admin_metrics import AdminMetricsRepository
from app.core.config import load_settings
from app.services.admin_bi import AdminBIService
from app.services.admin_charts import growth_chart
from app.services.admin_charts_stage25 import revenue_chart

router = Router(name="admin_stage25")


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

    metrics = await AdminMetricsRepository(session).statistics()
    chart_data = await AdminBIService(session).statistics()

    await message.answer_photo(
        BufferedInputFile(
            growth_chart(chart_data.points),
            filename="statistics.png",
        ),
        caption=(
            "📊 Статистика\n\n"
            f"• Всего — {number(metrics.users_total)}\n"
            f"• Живы — {number(metrics.users_alive)}\n"
            f"• Мёртвые — {number(metrics.users_dead)}\n\n"
            "👤 Статистика по времени\n\n"
            f"• За сегодня — {number(metrics.today)}\n"
            f"• За неделю — {number(metrics.week)}\n"
            f"• За месяц — {number(metrics.month)}\n\n"
            "📈 Органический прирост\n\n"
            f"• За сегодня — {number(metrics.organic_today)}\n"
            f"• За неделю — {number(metrics.organic_week)}\n"
            f"• За месяц — {number(metrics.organic_month)}\n\n"
            f"Активных карт — {number(metrics.active_cards)}"
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
            "👤 Статистика по прибыли\n\n"
            f"{row('За сегодня', metrics.today)}\n"
            f"{row('За неделю', metrics.week)}\n"
            f"{row('За месяц', metrics.month)}\n"
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

    alive_only = (callback.data or "").endswith(":alive")
    payload = await AdminMetricsRepository(session).export_user_ids(
        alive_only=alive_only
    )
    filename = "users-alive.txt" if alive_only else "users-all.txt"

    if callback.message:
        await callback.message.answer_document(
            BufferedInputFile(payload, filename=filename),
            caption="✅ Выгрузка готова",
        )
    await callback.answer()
