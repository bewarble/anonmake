from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import load_settings
from app.repositories.admin_control import AdminControlRepository

router = Router(name="admin_keyboard")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


def number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


@router.message(F.text == "📊 Статистика")
async def statistics(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    data = await AdminControlRepository(session).overview()
    await message.answer(
        "📊 Статистика\n\n"
        f"👥 Пользователи: {number(data.users_total)}\n"
        f"Новых за 24 часа: +{number(data.users_today)}\n\n"
        f"💌 Сообщений за 24 часа: +{number(data.questions_today)}\n"
        f"💬 Ответов за 24 часа: +{number(data.answers_today)}\n\n"
        f"⭐ Premium: {number(data.active_vip)}"
    )


@router.message(F.text == "👥 Пользователи")
async def users(message: Message) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    await message.answer(
        "👥 Пользователи\n\n"
        "Для поиска отправьте:\n"
        "/admin_find Telegram_ID\n\n"
        "Подробные карточки будут перенесены в веб-админку."
    )


@router.message(F.text == "💳 Финансы")
async def finance(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    data = await AdminControlRepository(session).overview()
    await message.answer(
        "💳 Финансы\n\n"
        f"Оплат за 24 часа: {number(data.payments_today)}\n"
        f"Выручка за 24 часа: {money(data.revenue_today_kopecks)} ₽"
    )


@router.message(F.text == "📨 Доставка")
async def delivery(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    data = await AdminControlRepository(session).overview()
    await message.answer(
        "📨 Доставка\n\n"
        f"В очереди: {number(data.delivery_pending)}\n"
        f"Ошибок: {number(data.delivery_failed)}"
    )


@router.message(F.text == "📢 Рассылки")
async def broadcasts(message: Message) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    await message.answer(
        "📢 Рассылки\n\n"
        "Используйте /broadcast для создания новой рассылки."
    )
