from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import answer_question_keyboard, main_menu_keyboard
from app.bot.states import AskQuestion
from app.repositories import QuestionRepository, UserRepository

router = Router(name="questions")
MAX_QUESTION_LENGTH = 1500


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Действие отменено.",
            reply_markup=main_menu_keyboard(),
        )


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_keyboard())


@router.message(AskQuestion.waiting_for_text, F.text)
async def receive_question(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.from_user is None:
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Вопрос не может быть пустым.")
        return
    if len(text) > MAX_QUESTION_LENGTH:
        await message.answer(
            f"Слишком длинный вопрос. Максимум — {MAX_QUESTION_LENGTH} символов."
        )
        return

    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    if not isinstance(recipient_id, int):
        await state.clear()
        await message.answer(
            "Сессия устарела. Откройте персональную ссылку ещё раз.",
            reply_markup=main_menu_keyboard(),
        )
        return

    users = UserRepository(session)
    sender = await users.upsert_from_telegram(message.from_user)
    recipient = await users.get_by_id(recipient_id)

    if recipient is None:
        await state.clear()
        await message.answer(
            "Получатель больше не найден.",
            reply_markup=main_menu_keyboard(),
        )
        return

    if sender.id == recipient.id:
        await state.clear()
        await message.answer(
            "Нельзя отправить вопрос самому себе.",
            reply_markup=main_menu_keyboard(),
        )
        return

    question = await QuestionRepository(session).create(
        sender_id=sender.id,
        recipient_id=recipient.id,
        text=text,
    )
    await session.commit()

    try:
        await bot.send_message(
            recipient.telegram_id,
            "📩 Вам пришёл новый анонимный вопрос:\n\n"
            f"{question.text}",
            reply_markup=answer_question_keyboard(question.id),
        )
    except Exception:
        question.status = "delivery_failed"
        await session.commit()
        await state.clear()
        await message.answer(
            "Не удалось доставить вопрос. Возможно, получатель заблокировал бота.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        "✅ Вопрос отправлен анонимно.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(AskQuestion.waiting_for_text)
async def question_requires_text(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте вопрос текстовым сообщением.")
