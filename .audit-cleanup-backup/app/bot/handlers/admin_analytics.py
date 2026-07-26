from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_analytics import analytics_keyboard
from app.core.config import load_settings
from app.services.analytics import AnalyticsService

router = Router(name="admin_analytics")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


def format_int(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def format_money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


async def safe_edit(callback: CallbackQuery, text: str) -> None:
    if callback.message is None:
        return

    try:
        await callback.message.edit_text(
            text,
            reply_markup=analytics_keyboard(),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


@router.callback_query(F.data == "admin:analytics")
async def analytics_dashboard(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    data = await AnalyticsService(session).snapshot()

    text = (
        "📈 Аналитика\n\n"
        "👥 Пользователи\n"
        f"Всего: {format_int(data.users_total)}\n"
        f"24 ч: +{format_int(data.users_1d)}\n"
        f"7 дней: +{format_int(data.users_7d)}\n"
        f"30 дней: +{format_int(data.users_30d)}\n\n"
        "💌 Сообщения\n"
        f"Всего: {format_int(data.questions_total)}\n"
        f"24 ч: +{format_int(data.questions_1d)}\n"
        f"7 дней: +{format_int(data.questions_7d)}\n"
        f"30 дней: +{format_int(data.questions_30d)}\n\n"
        "💬 Ответы\n"
        f"Всего: {format_int(data.answers_total)}\n"
        f"24 ч: +{format_int(data.answers_1d)}\n"
        f"Конверсия в ответ: {data.answer_rate:.1f}%\n\n"
        "👑 Premium\n"
        f"Активно: {format_int(data.active_vip)}\n"
        f"Раскрытий: {format_int(data.reveals_total)}\n"
        f"Конверсия в Premium: {data.vip_rate:.2f}%\n"
        f"Конверсия в раскрытие: {data.reveal_rate:.2f}%\n\n"
        "💳 Платежи\n"
        f"Успешно: {format_int(data.payments_success)}\n"
        f"Ошибки: {format_int(data.payments_failed)}\n"
        f"Выручка: {format_money(data.revenue_kopecks)} ₽"
    )

    await safe_edit(callback, text)
    await callback.answer()
