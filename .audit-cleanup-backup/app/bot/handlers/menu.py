from aiogram import F, Router
from aiogram.types import Message

router = Router(name=__name__)


@router.message(F.text == "🔗 Моя ссылка")
async def show_personal_link(message: Message) -> None:
    bot = await message.bot.get_me()

    await message.answer(
        "Ваша персональная ссылка пока формируется.\n\n"
        f"https://t.me/{bot.username}?start=ask_{message.from_user.id}"
    )


@router.message(F.text == "📥 Мои вопросы")
async def show_questions(message: Message) -> None:
    await message.answer("У вас пока нет анонимных вопросов.")


@router.message(F.text == "⭐ Подписка")
async def show_subscription(message: Message) -> None:
    await message.answer(
        "Платная подписка появится на следующем этапе разработки."
    )


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message) -> None:
    await message.answer("Настройки пока не добавлены.")
