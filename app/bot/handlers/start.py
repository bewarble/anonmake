from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import cancel_keyboard, main_menu_keyboard
from app.bot.states import AskQuestion
from app.core import texts
from app.repositories import UserRepository

router = Router(name="start")


async def personal_link(bot: Bot, public_code: str) -> str:
    bot_user = await bot.get_me()
    return f"https://t.me/{bot_user.username}?start={public_code}"


@router.message(CommandStart())
async def command_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.from_user is None:
        return

    await state.clear()
    users = UserRepository(session)
    current_user = await users.upsert_from_telegram(message.from_user)

    code = (command.args or "").strip()
    if not code:
        link = await personal_link(bot, current_user.public_code)
        await message.answer(
            f"{texts.WELCOME}\n\n"
            f"{texts.PERSONAL_LINK.format(link=link)}\n\n"
            f"{texts.PERSONAL_LINK_HINT}",
            reply_markup=main_menu_keyboard(),
        )
        return

    recipient = await users.get_by_public_code(code)
    if recipient is None:
        await message.answer(
            texts.INVALID_LINK,
            reply_markup=main_menu_keyboard(),
        )
        return

    if recipient.id == current_user.id:
        await message.answer(
            texts.SELF_MESSAGE,
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.set_state(AskQuestion.waiting_for_text)
    await state.update_data(recipient_id=recipient.id)
    await message.answer(
        f"{texts.QUESTION_PROMPT}\n\n{texts.QUESTION_HINT}",
        reply_markup=cancel_keyboard(),
    )


@router.message(F.text == "🔗 Моя ссылка")
async def show_personal_link(
    message: Message,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.from_user is None:
        return

    user = await UserRepository(session).upsert_from_telegram(message.from_user)
    link = await personal_link(bot, user.public_code)
    await message.answer(
        f"{texts.PERSONAL_LINK.format(link=link)}\n\n"
        f"{texts.PERSONAL_LINK_HINT}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text.in_({"✨ Как это работает", "📥 Как это работает", "ℹ️ Помощь"}))
async def show_help(message: Message) -> None:
    await message.answer(
        texts.HELP,
        reply_markup=main_menu_keyboard(),
    )
