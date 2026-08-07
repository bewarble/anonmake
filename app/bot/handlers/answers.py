from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import cancel_keyboard, main_menu_for
from app.bot.keyboards.questions import answer_received_keyboard, answer_share_keyboard
from app.bot.states import AnswerQuestion, AskQuestion
from app.core import texts
from app.core.bot_context import require_current_bot
from app.repositories import AnswerRepository, QuestionRepository, UserRepository
from app.repositories.delivery import DeliveryRepository
from app.services.crm_tracking import CrmTrackingService
from app.services.delivery import serialize_markup

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
        await callback.answer(texts.INVALID_LINK, show_alert=True)
        return

    question = await QuestionRepository(session).get_with_users(question_id)
    current_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if question is None or current_user is None or question.recipient_id != current_user.id:
        await state.clear()
        await callback.answer(texts.ANSWER_NOT_FOUND, show_alert=True)
        return

    await state.set_state(AnswerQuestion.waiting_for_text)
    await state.update_data(question_id=question.id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(texts.ANSWER_PROMPT, reply_markup=cancel_keyboard())


@router.callback_query(F.data.startswith("answer_back:"))
async def begin_answer_back(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.from_user is None:
        return
    try:
        question_id = int((callback.data or "").split(":", 1)[1])
    except (IndexError, ValueError):
        await state.clear()
        await callback.answer(texts.INVALID_LINK, show_alert=True)
        return

    question = await QuestionRepository(session).get_with_users(question_id)
    current_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if question is None or current_user is None or question.sender_id != current_user.id:
        await state.clear()
        await callback.answer(texts.ANSWER_NOT_FOUND, show_alert=True)
        return

    await state.set_state(AskQuestion.waiting_for_text)
    await state.update_data(recipient_id=question.recipient_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(texts.QUESTION_PROMPT, reply_markup=cancel_keyboard())


@router.message(AnswerQuestion.waiting_for_text, F.text)
async def receive_answer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None:
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer(texts.ANSWER_EMPTY)
        return
    if len(text) > MAX_ANSWER_LENGTH:
        await message.answer(texts.ANSWER_TOO_LONG.format(limit=MAX_ANSWER_LENGTH))
        return

    data = await state.get_data()
    question_id = data.get("question_id")
    if not isinstance(question_id, int):
        await state.clear()
        await message.answer(texts.ANSWER_SESSION_EXPIRED, reply_markup=main_menu_for(message.from_user.id))
        return

    # Lock the source message while appending a reply so concurrent submissions
    # remain ordered, but do not impose a one-reply-per-message limit.
    question = await QuestionRepository(session).get_with_users(question_id, for_update=True)
    current_user = await UserRepository(session).upsert_from_telegram(message.from_user)
    if question is None or question.recipient_id != current_user.id:
        await state.clear()
        await message.answer(texts.ANSWER_NOT_FOUND, reply_markup=main_menu_for(message.from_user.id))
        return

    answer = await AnswerRepository(session).create(question=question, text=text)
    await DeliveryRepository(session).enqueue(
        kind="answer",
        dedupe_key=f"answer:{answer.id}",
        chat_id=question.sender.telegram_id,
        text=texts.ANSWER_RECEIVED.format(answer=text),
        reply_markup=serialize_markup(answer_received_keyboard(question.id)),
    )

    tracking = CrmTrackingService(session)
    await tracking.answer_sent(user_id=current_user.id, answer_id=answer.id)
    await tracking.answer_received(user_id=question.sender_id, answer_id=answer.id)
    await session.commit()

    await state.clear()
    current_bot = require_current_bot()
    personal_link = f"https://t.me/{current_bot.username}?start={current_user.public_code}"
    await message.answer(
        texts.ANSWER_SENT,
        reply_markup=answer_share_keyboard(personal_link),
    )


@router.message(AnswerQuestion.waiting_for_text)
async def answer_requires_text(message: Message) -> None:
    await message.answer(texts.TEXT_ONLY)
