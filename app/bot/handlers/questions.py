from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import answer_question_keyboard, main_menu_keyboard
from app.bot.states import AskQuestion
from app.core import texts
from app.core.config import load_settings
from app.repositories import QuestionRepository, UserRepository
from app.repositories.delivery import DeliveryRepository
from app.services.abuse_guard import AbuseGuard
from app.services.delivery import serialize_markup
from app.services.redis_client import get_redis

router = Router(name="questions")
logger = logging.getLogger(__name__)
MAX_QUESTION_LENGTH = 1500


def build_guard() -> AbuseGuard:
    settings = load_settings()
    return AbuseGuard(
        get_redis(settings.redis_url),
        burst_limit=settings.question_burst_limit,
        burst_window_seconds=settings.question_burst_window_seconds,
        minute_limit=settings.question_minute_limit,
        duplicate_window_seconds=settings.question_duplicate_window_seconds,
    )


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer(texts.CANCELLED)
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            texts.CANCELLED,
            reply_markup=main_menu_keyboard(),
        )


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())


@router.message(AskQuestion.waiting_for_text, F.text)
async def receive_question(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None:
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer(texts.QUESTION_EMPTY)
        return
    if len(text) > MAX_QUESTION_LENGTH:
        await message.answer(
            texts.QUESTION_TOO_LONG.format(limit=MAX_QUESTION_LENGTH)
        )
        return

    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    if not isinstance(recipient_id, int):
        await state.clear()
        await message.answer(
            texts.QUESTION_SESSION_EXPIRED,
            reply_markup=main_menu_keyboard(),
        )
        return

    settings = load_settings()
    guard: AbuseGuard | None = None

    if settings.abuse_guard_enabled:
        guard = build_guard()
        try:
            decision = await guard.check_question(
                sender_telegram_id=message.from_user.id,
                recipient_user_id=recipient_id,
                text=text,
            )
        except Exception:
            logger.exception("Question abuse guard is unavailable")
        else:
            if not decision.allowed:
                if decision.reason == "duplicate":
                    await message.answer(texts.QUESTION_DUPLICATE)
                else:
                    await message.answer(texts.QUESTION_TOO_FAST)
                return

    users = UserRepository(session)
    sender = await users.upsert_from_telegram(message.from_user)
    recipient = await users.get_by_id(recipient_id)

    if recipient is None:
        await state.clear()
        await message.answer(
            texts.QUESTION_RECIPIENT_MISSING,
            reply_markup=main_menu_keyboard(),
        )
        return

    if sender.id == recipient.id:
        await state.clear()
        await message.answer(
            texts.SELF_MESSAGE,
            reply_markup=main_menu_keyboard(),
        )
        return

    try:
        question = await QuestionRepository(session).create(
            sender_id=sender.id,
            recipient_id=recipient.id,
            text=text,
        )
        question.status = "queued"

        markup = answer_question_keyboard(question.id)
        await DeliveryRepository(session).enqueue(
            kind="question",
            dedupe_key=f"question:{question.id}",
            chat_id=recipient.telegram_id,
            text=texts.NEW_QUESTION.format(text=question.text),
            reply_markup=serialize_markup(markup),
        )
        await session.commit()
    except Exception:
        await session.rollback()
        if guard is not None:
            try:
                await guard.rollback_duplicate(
                    sender_telegram_id=message.from_user.id,
                    recipient_user_id=recipient_id,
                    text=text,
                )
            except Exception:
                logger.exception("Could not rollback duplicate key")
        raise

    await state.clear()
    await message.answer(
        texts.QUESTION_SENT,
        reply_markup=main_menu_keyboard(),
    )


@router.message(AskQuestion.waiting_for_text)
async def question_requires_text(message: Message) -> None:
    await message.answer(texts.TEXT_ONLY)
