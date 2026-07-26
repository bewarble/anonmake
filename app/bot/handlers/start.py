from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import get_main_menu

router = Router(name=__name__)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    first_name = (
        message.from_user.first_name
        if message.from_user
        else "пользователь"
    )

    await message.answer(
        f"Привет, {first_name}! 👋\n\n"
        "Здесь ты сможешь получать анонимные вопросы "
        "по персональной ссылке.",
        reply_markup=get_main_menu(),
    )
