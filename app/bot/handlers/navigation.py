from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu_for
from app.bot.ui import USER_HELP
from app.core import texts

router = Router(name="navigation")
fallback_router = Router(name="navigation_fallback")


def menu_for(message: Message):
    return main_menu_for(message.from_user.id if message.from_user else None)


@router.message(F.text == USER_HELP)
async def show_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.HELP, reply_markup=menu_for(message))


@fallback_router.callback_query()
async def stale_callback(callback: CallbackQuery) -> None:
    # Old inline keyboards can survive deployments for months. Always stop the
    # Telegram spinner and give a clean user-facing recovery path.
    await callback.answer(texts.BUTTON_EXPIRED, show_alert=True)


@fallback_router.message()
async def unknown_input(message: Message) -> None:
    await message.answer(texts.UNKNOWN_INPUT, reply_markup=menu_for(message))
