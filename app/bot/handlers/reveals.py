from __future__ import annotations

import logging
from datetime import timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reveals import (
    reveal_checkout_keyboard,
    reveal_consent_keyboard,
)
from app.core import texts
from app.core.config import load_settings
from app.repositories import QuestionRepository, UserRepository
from app.repositories.billing import BillingRepository
from app.repositories.reveals import RevealRepository
from app.services.crm_tracking import CrmTrackingService
from app.services.impaya import ImpayaClient
from app.services.reveal_checkout import RevealCheckoutService
from app.services.sender_identity import resolve_current_sender
from app.services.vip import has_active_vip

router = Router(name="reveals")
logger = logging.getLogger(__name__)


def build_client(settings) -> ImpayaClient:
    return ImpayaClient(
        settings.impaya_api_url,
        settings.impaya_api_token,
        settings.impaya_binding_terminal_name or settings.impaya_terminal_name,
        auth_header=settings.impaya_auth_header,
        auth_prefix=settings.impaya_auth_prefix,
        protocol_version=settings.impaya_protocol_version,
        recurrent_terminal_name=(
            settings.impaya_recurrent_terminal_name
            or settings.impaya_terminal_name
        ),
    )


async def _load_reveal_context(
    callback: CallbackQuery,
    session: AsyncSession,
    *,
    question_id: int,
    context: str,
):
    buyer = await UserRepository(session).upsert_from_telegram(callback.from_user)
    question = await QuestionRepository(session).get_with_users(question_id)

    if question is None:
        return buyer, None, None
    if context == "question" and question.recipient_id == buyer.id:
        return buyer, question, question.sender
    if context == "answer" and question.sender_id == buyer.id:
        return buyer, question, question.recipient
    return buyer, None, None


async def _deliver_identity(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    *,
    buyer,
    question,
    target,
) -> None:
    identity = await resolve_current_sender(bot, target)
    await CrmTrackingService(session).sender_revealed(
        user_id=buyer.id,
        question_id=question.id,
    )
    await session.commit()
    await callback.answer()
    if callback.message:
        await callback.message.answer(texts.VIP_SENDER.format(sender=identity.label))


async def _show_or_reveal(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    *,
    question_id: int,
    context: str,
) -> None:
    buyer, question, target = await _load_reveal_context(
        callback,
        session,
        question_id=question_id,
        context=context,
    )
    if question is None or target is None:
        await callback.answer(texts.ANSWER_NOT_FOUND, show_alert=True)
        return

    subscription = await BillingRepository(session).subscription_for_user(buyer.id)
    if has_active_vip(subscription):
        await _deliver_identity(
            callback,
            session,
            bot,
            buyer=buyer,
            question=question,
            target=target,
        )
        return

    await callback.answer()
    if callback.message:
        await callback.message.answer(
            texts.REVEAL_CONSENT,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=reveal_consent_keyboard(
                question_id=question.id,
                context=context,
            ),
        )


@router.callback_query(F.data.startswith("reveal:"))
async def reveal_sender(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    try:
        question_id = int((callback.data or "").split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.INVALID_LINK, show_alert=True)
        return
    await _show_or_reveal(
        callback,
        session,
        bot,
        question_id=question_id,
        context="question",
    )


@router.callback_query(F.data.startswith("reveal_answer:"))
async def reveal_answerer(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    try:
        question_id = int((callback.data or "").split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.INVALID_LINK, show_alert=True)
        return
    await _show_or_reveal(
        callback,
        session,
        bot,
        question_id=question_id,
        context="answer",
    )


@router.callback_query(F.data == "reveal_close")
async def close_reveal(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            # Repeated taps / old messages are normal user behavior, not incidents.
            pass


@router.callback_query(F.data.startswith("reveal_confirm:"))
async def confirm_reveal(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3 or parts[1] not in {"question", "answer"}:
        await callback.answer(texts.INVALID_LINK, show_alert=True)
        return

    context = parts[1]
    try:
        question_id = int(parts[2])
    except ValueError:
        await callback.answer(texts.INVALID_LINK, show_alert=True)
        return

    buyer, question, target = await _load_reveal_context(
        callback,
        session,
        question_id=question_id,
        context=context,
    )
    if question is None or target is None:
        await callback.answer(texts.ANSWER_NOT_FOUND, show_alert=True)
        return

    # The user may return to an old consent button after payment already finished.
    # In that case reveal immediately instead of attempting another checkout.
    subscription = await BillingRepository(session).subscription_for_user(buyer.id)
    if has_active_vip(subscription):
        await _deliver_identity(
            callback,
            session,
            bot,
            buyer=buyer,
            question=question,
            target=target,
        )
        return

    settings = load_settings()
    if not settings.billing_enabled:
        await callback.answer(texts.VIP_PAYMENT_UNAVAILABLE, show_alert=True)
        return
    if (
        not settings.impaya_api_token.strip()
        or not settings.impaya_payment_form_url_template.strip()
        or not settings.public_base_url.strip()
    ):
        await callback.answer(texts.VIP_CONFIGURATION_ERROR, show_alert=True)
        return

    checkout = await RevealRepository(session).get_or_create(
        question_id=question.id,
        buyer_id=buyer.id,
    )
    public_base = settings.public_base_url.rstrip("/")
    success_url = f"{public_base}/payments/return/success/{checkout.token}"
    fail_url = f"{public_base}/payments/return/fail/{checkout.token}"

    client = build_client(settings)
    try:
        payment_url = await RevealCheckoutService(
            session,
            client,
            payment_form_url_template=settings.impaya_payment_form_url_template,
            trial_amount=settings.trial_price_kopecks,
            trial_duration=timedelta(hours=settings.trial_duration_hours),
        ).create(
            checkout,
            user_id=buyer.id,
            success_url=success_url,
            fail_url=fail_url,
        )
    except Exception:
        logger.exception(
            "Could not create reveal checkout",
            extra={"telegram_user_id": callback.from_user.id},
        )
        await callback.answer(texts.VIP_PAYMENT_UNAVAILABLE, show_alert=True)
        return
    finally:
        await client.close()

    await callback.answer()
    if callback.message:
        try:
            await callback.message.edit_text(
                texts.REVEAL_PAYMENT_READY,
                reply_markup=reveal_checkout_keyboard(payment_url=payment_url),
            )
        except TelegramBadRequest as exc:
            # "message is not modified" after a double tap is benign. Other edit
            # failures should still be visible in logs and global diagnostics.
            if "message is not modified" not in str(exc).lower():
                raise
