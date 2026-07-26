from __future__ import annotations

from datetime import timezone
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_control import (
    control_center_keyboard,
    payment_details_keyboard,
    payments_keyboard,
    subscriptions_keyboard,
    users_filters_keyboard,
)
from app.core.config import load_settings
from app.repositories.admin_control import AdminControlRepository

router = Router(name="admin_control")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


def number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


async def safe_edit(callback: CallbackQuery, text: str, reply_markup) -> None:
    if callback.message is None:
        return

    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


@router.callback_query(F.data == "adminx:home")
async def control_home(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    data = await AdminControlRepository(session).overview()
    text = (
        "🛠 Центр управления\n\n"
        f"👥 Пользователи: {number(data.users_total)} "
        f"(+{number(data.users_today)} за 24 ч)\n"
        f"💌 Сообщения: +{number(data.questions_today)}\n"
        f"💬 Ответы: +{number(data.answers_today)}\n"
        f"👑 Активный VIP: {number(data.active_vip)}\n\n"
        f"💳 Платежи за 24 ч: {number(data.payments_today)}\n"
        f"💰 Выручка за 24 ч: {money(data.revenue_today_kopecks)} ₽\n\n"
        f"📨 В очереди: {number(data.delivery_pending)}\n"
        f"❌ Ошибки доставки: {number(data.delivery_failed)}"
    )

    await safe_edit(callback, text, control_center_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adminx:users:"))
async def control_users(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer("Некорректный фильтр", show_alert=True)
        return

    filter_name = parts[2]
    try:
        page = max(0, int(parts[3]))
    except ValueError:
        page = 0

    if filter_name not in {"recent", "vip", "paid", "inactive"}:
        filter_name = "recent"

    users, has_next = await AdminControlRepository(session).users(
        filter_name=filter_name,
        page=page,
    )
    title = {
        "recent": "Новые пользователи",
        "vip": "Пользователи с VIP",
        "paid": "Пользователи с платежами",
        "inactive": "Неактивные пользователи",
    }[filter_name]

    await safe_edit(
        callback,
        f"👥 {title}\n\nСтраница {page + 1}",
        users_filters_keyboard(
            users,
            filter_name=filter_name,
            page=page,
            has_next=has_next,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adminx:payments:"))
async def control_payments(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer("Некорректный фильтр", show_alert=True)
        return

    filter_name = parts[2]
    try:
        page = max(0, int(parts[3]))
    except ValueError:
        page = 0

    if filter_name not in {"all", "success", "failed", "pending"}:
        filter_name = "all"

    rows, has_next = await AdminControlRepository(session).payments(
        filter_name=filter_name,
        page=page,
    )

    await safe_edit(
        callback,
        f"💳 Платежи\n\nФильтр: {filter_name}\nСтраница {page + 1}",
        payments_keyboard(
            rows,
            filter_name=filter_name,
            page=page,
            has_next=has_next,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adminx:subs:"))
async def control_subscriptions(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer("Некорректный фильтр", show_alert=True)
        return

    filter_name = parts[2]
    try:
        page = max(0, int(parts[3]))
    except ValueError:
        page = 0

    if filter_name not in {"active", "renewal", "cancelled", "expired"}:
        filter_name = "active"

    rows, has_next = await AdminControlRepository(session).subscriptions(
        filter_name=filter_name,
        page=page,
    )

    await safe_edit(
        callback,
        f"👑 Подписки\n\nФильтр: {filter_name}\nСтраница {page + 1}",
        subscriptions_keyboard(
            rows,
            filter_name=filter_name,
            page=page,
            has_next=has_next,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adminx:payment:"))
async def payment_details(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    try:
        attempt_id = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    row = await AdminControlRepository(session).payment_details(attempt_id)
    if row is None:
        await callback.answer("Платёж не найден", show_alert=True)
        return

    attempt = row.attempt
    username = (
        f"@{escape(row.user.username)}"
        if row.user.username
        else f"ID {row.user.id}"
    )
    created = attempt.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    text = (
        "💳 Платёж\n\n"
        f"ID: {attempt.id}\n"
        f"Пользователь: {username}\n"
        f"Сумма: {money(attempt.amount_kopecks)} ₽\n"
        f"Статус: {escape(attempt.status)}\n"
        f"Тип: {escape(attempt.attempt_kind)}\n"
        f"Цикл: {escape(attempt.billing_cycle_key)}\n"
        f"Создан: {created.astimezone(timezone.utc):%d.%m.%Y %H:%M UTC}\n"
        f"Операция: {escape(attempt.customer_operation_id)}"
    )

    if attempt.error_code:
        text += f"\nКод ошибки: {escape(attempt.error_code)}"
    if attempt.error_message:
        text += f"\nОшибка: {escape(attempt.error_message[:300])}"

    await safe_edit(
        callback,
        text,
        payment_details_keyboard(row.user.id),
    )
    await callback.answer()
