from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_minimal import (
    admin_home_keyboard,
    finance_keyboard,
    growth_keyboard,
    operations_keyboard,
    users_keyboard,
)
from app.core import admin_texts
from app.core.config import load_settings
from app.repositories.admin_control import AdminControlRepository

router = Router(name="admin_minimal")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


def number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


async def overview_text(session: AsyncSession) -> str:
    data = await AdminControlRepository(session).overview()
    return admin_texts.OVERVIEW.format(
        users=number(data.users_total),
        new_users=number(data.users_today),
        questions=number(data.questions_today),
        answers=number(data.answers_today),
        vip=number(data.active_vip),
        payments=number(data.payments_today),
        revenue=money(data.revenue_today_kopecks),
        pending=number(data.delivery_pending),
        failed=number(data.delivery_failed),
    )


async def safe_edit(callback: CallbackQuery, text: str, reply_markup) -> None:
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


@router.message(Command("admin"))
async def admin_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await message.answer(admin_texts.ADMIN_UNAVAILABLE)
        return
    await message.answer(
        await overview_text(session),
        reply_markup=admin_home_keyboard(),
    )


@router.callback_query(F.data == "adm:home")
async def admin_home(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.ADMIN_UNAVAILABLE, show_alert=True)
        return
    await safe_edit(callback, await overview_text(session), admin_home_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:users")
async def admin_users(callback: CallbackQuery) -> None:
    await safe_edit(callback, admin_texts.SECTION_USERS, users_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:growth")
async def admin_growth(callback: CallbackQuery) -> None:
    await safe_edit(callback, admin_texts.SECTION_GROWTH, growth_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:finance")
async def admin_finance(callback: CallbackQuery) -> None:
    await safe_edit(callback, admin_texts.SECTION_FINANCE, finance_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:operations")
async def admin_operations(callback: CallbackQuery) -> None:
    await safe_edit(callback, admin_texts.SECTION_OPERATIONS, operations_keyboard())
    await callback.answer()
