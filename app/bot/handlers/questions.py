from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import answer_question_keyboard, main_menu_for
from app.bot.states import AskQuestion
from app.core import texts
from app.core.config import load_settings
from app.repositories import QuestionRepository, UserRepository
from app.repositories.delivery import DeliveryRepository
from app.services.abuse_guard import AbuseGuard
from app.services.crm_tracking import CrmTrackingService
from app.services.delivery import serialize_markup
from app.services.redis_client import get_redis
from app.services.telegram_content import delivery_payload, extract_content

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


@router.callback_query(lambda callback: callback.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer(texts.CANCELLED)
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
        await callback.message.answer(
            texts.CANCELLED,
            reply_markup=main_menu_for(callback.from_user.id),
        )


@router.message(AskQuestion.waiting_for_text)
async def receive_question(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None:
        return

    content = extract_content(message)
    if content is None:
        await message.answer(texts.TEXT_ONLY)
        return

    if len(content.text) > MAX_QUESTION_LENGTH:
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
            reply_markup=main_menu_for(message.from_user.id),
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
                text=content.duplicate_key,
            )
        except Exception:
            logger.exception("Question abuse guard is unavailable")
        else:
            if not decision.allowed:
                await message.answer(
                    texts.QUESTION_DUPLICATE
                    if decision.reason == "duplicate"
                    else texts.QUESTION_TOO_FAST
                )
                return

    users = UserRepository(session)
    sender = await users.upsert_from_telegram(message.from_user)
    recipient = await users.get_by_id(recipient_id)

    if recipient is None:
        await state.clear()
        await message.answer(
            texts.QUESTION_RECIPIENT_MISSING,
            reply_markup=main_menu_for(message.from_user.id),
        )
        return

    if sender.id == recipient.id:
        await state.clear()
        await message.answer(
            texts.SELF_MESSAGE,
            reply_markup=main_menu_for(message.from_user.id),
        )
        return

    try:
        question = await QuestionRepository(session).create(
            sender_id=sender.id,
            recipient_id=recipient.id,
            text=content.text,
            content_type=content.content_type,
            media_file_id=content.file_id,
            media_caption=content.caption,
        )
        question.status = "queued"

        markup = answer_question_keyboard(question.id)
        delivery_text = (
            texts.NEW_QUESTION.format(text=question.text)
            if content.content_type == "text"
            else "💌 Новое анонимное сообщение"
        )
        await DeliveryRepository(session).enqueue(
            kind="question",
            dedupe_key=f"question:{question.id}",
            chat_id=recipient.telegram_id,
            text=delivery_text,
            reply_markup=serialize_markup(markup),
            payload=delivery_payload(content),
        )

        tracking = CrmTrackingService(session)
        await tracking.question_sent(
            user_id=sender.id,
            question_id=question.id,
        )
        await tracking.question_received(
            user_id=recipient.id,
            question_id=question.id,
        )

        await session.commit()
    except Exception:
        await session.rollback()
        if guard is not None:
            try:
                await guard.rollback_duplicate(
                    sender_telegram_id=message.from_user.id,
                    recipient_user_id=recipient_id,
                    text=content.duplicate_key,
                )
            except Exception:
                logger.exception("Could not rollback duplicate key")
        raise

    await state.clear()
    await message.answer(
        texts.QUESTION_SENT,
        reply_markup=main_menu_for(message.from_user.id),
    )
