from __future__ import annotations

from datetime import timezone
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_users import (
    user_card_keyboard,
    users_list_keyboard,
)
from app.core.config import load_settings
from app.repositories.admin_users import AdminUsersRepository

router = Router(name="admin_users")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


async def safe_edit(callback: CallbackQuery, text: str, reply_markup) -> None:
    if callback.message is None:
        return

    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


@router.callback_query(F.data.startswith("admin:users:"))
async def users_page(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    try:
        page = max(0, int((callback.data or "").rsplit(":", 1)[1]))
    except ValueError:
        page = 0

    users, has_next = await AdminUsersRepository(session).recent_users(
        page=page
    )

    text = (
        "👥 Пользователи\n\n"
        f"Страница {page + 1}\n"
        "Выберите пользователя для подробной карточки."
    )

    await safe_edit(
        callback,
        text,
        users_list_keyboard(users, page=page, has_next=has_next),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:"))
async def user_card(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    try:
        user_id = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    card = await AdminUsersRepository(session).get_card(user_id)
    if card is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    user = card.user
    username = f"@{escape(user.username)}" if user.username else "—"
    name = escape(user.first_name or "—")

    vip_status = "не активен"
    if card.vip_active and card.subscription is not None:
        value = card.subscription.access_until
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            vip_status = value.astimezone(timezone.utc).strftime(
                "до %d.%m.%Y %H:%M UTC"
            )

    text = (
        "👤 Пользователь\n\n"
        f"ID: {user.id}\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Username: {username}\n"
        f"Имя: {name}\n\n"
        f"Отправлено сообщений: {card.questions_sent}\n"
        f"Получено сообщений: {card.questions_received}\n"
        f"Отправлено ответов: {card.answers_sent}\n"
        f"Раскрытий: {card.reveals}\n\n"
        f"VIP: {vip_status}\n"
        f"Успешных платежей: {card.successful_payments}\n"
        f"Сумма платежей: {money(card.revenue_kopecks)} ₽"
    )

    await safe_edit(
        callback,
        text,
        user_card_keyboard(user.id),
    )
    await callback.answer()
