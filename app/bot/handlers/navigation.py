from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu_for
from app.core import texts

router = Router(name="navigation")
fallback_router = Router(name="navigation_fallback")


def menu_for(message: Message):
    return main_menu_for(message.from_user.id if message.from_user else None)


@fallback_router.callback_query()
async def stale_callback(callback: CallbackQuery) -> None:
    # Old inline keyboards can survive deployments for months. Always stop the
    # Telegram spinner and give a clean user-facing recovery path.
    await callback.answer(texts.BUTTON_EXPIRED, show_alert=True)


@fallback_router.message()
async def unknown_input(message: Message) -> None:
    await message.answer(texts.UNKNOWN_INPUT, reply_markup=menu_for(message))
