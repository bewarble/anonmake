from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import cancel_keyboard, main_menu_keyboard
from app.bot.states import AnswerQuestion
from app.repositories import AnswerRepository, QuestionRepository, UserRepository

router = Router(name="answers")
MAX_ANSWER_LENGTH = 1500


@router.callback_query(F.data.startswith("answer:"))
async def begin_answer(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or callback.data is None:
        return

    try:
        question_id = int(callback.data.split(":", maxsplit=1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный вопрос", show_alert=True)
        return

    question = await QuestionRepository(session).get_with_users(question_id)
    current_user = await UserRepository(session).get_by_telegram_id(
        callback.from_user.id
    )

    if question is None or current_user is None:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    if question.recipient_id != current_user.id:
        await callback.answer("Это не ваш вопрос", show_alert=True)
        return
    if question.answer is not None:
        await callback.answer("На этот вопрос уже был дан ответ", show_alert=True)
        return

    await state.set_state(AnswerQuestion.waiting_for_text)
    await state.update_data(question_id=question.id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Напишите ответ одним текстовым сообщением.",
            reply_markup=cancel_keyboard(),
        )


@router.message(AnswerQuestion.waiting_for_text, F.text)
async def receive_answer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.from_user is None:
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Ответ не может быть пустым.")
        return
    if len(text) > MAX_ANSWER_LENGTH:
        await message.answer(
            f"Слишком длинный ответ. Максимум — {MAX_ANSWER_LENGTH} символов."
        )
        return

    data = await state.get_data()
    question_id = data.get("question_id")
    if not isinstance(question_id, int):
        await state.clear()
        await message.answer(
            "Сессия устарела.",
            reply_markup=main_menu_keyboard(),
        )
        return

    question = await QuestionRepository(session).get_with_users(question_id)
    current_user = await UserRepository(session).upsert_from_telegram(
        message.from_user
    )

    if question is None or question.recipient_id != current_user.id:
        await state.clear()
        await message.answer(
            "Вопрос не найден.",
            reply_markup=main_menu_keyboard(),
        )
        return
    if question.answer is not None:
        await state.clear()
        await message.answer(
            "На этот вопрос уже был дан ответ.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await AnswerRepository(session).create(question=question, text=text)
    await session.commit()

    try:
        await bot.send_message(
            question.sender.telegram_id,
            "💬 Получен ответ на ваш анонимный вопрос:\n\n"
            f"❓ {question.text}\n\n"
            f"✅ {text}",
        )
    except Exception:
        await state.clear()
        await message.answer(
            "Ответ сохранён, но отправитель сейчас недоступен.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        "✅ Ответ отправлен.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(AnswerQuestion.waiting_for_text)
async def answer_requires_text(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте ответ текстовым сообщением.")
