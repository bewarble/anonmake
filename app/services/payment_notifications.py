from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import texts
from app.core.bot_context import CurrentBot, reset_current_bot, set_current_bot
from app.core.config import load_settings
from app.models.bot_instance import BotInstance
from app.models.reveal import RevealCheckout
from app.models.user import User
from app.repositories import QuestionRepository, UserRepository
from app.services.bot_credentials import resolve_bot_token
from app.services.crm_tracking import CrmTrackingService
from app.services.impaya import ImpayaClient
from app.services.reveal_checkout import RevealCheckoutService
from app.services.sender_identity import resolve_current_sender

logger = logging.getLogger(__name__)


async def finalize_checkout_and_notify(
    session: AsyncSession,
    client: ImpayaClient,
    checkout: RevealCheckout,
    *,
    payment_form_url_template: str,
) -> str:
    """Finalize a reveal payment in the bot/project that owns the checkout."""
    settings = load_settings()

    buyer_row = await session.get(User, checkout.buyer_id)
    if buyer_row is None:
        checkout.notification_error = "Buyer was not found"
        await session.commit()
        return "notification_failed"

    instance = await session.get(BotInstance, buyer_row.bot_id)
    if instance is None:
        checkout.notification_error = "Bot instance was not found"
        await session.commit()
        return "notification_failed"

    token = await resolve_bot_token(session, settings, instance)
    bot = Bot(token=token)
    context_token = set_current_bot(
        CurrentBot(instance.id, instance.code, instance.username, instance.display_name)
    )
    try:
        paid = await RevealCheckoutService(
            session,
            client,
            payment_form_url_template=payment_form_url_template,
            trial_amount=settings.trial_price_kopecks,
            trial_duration=timedelta(hours=settings.trial_duration_hours),
        ).finalize(checkout, user_id=checkout.buyer_id)

        if not paid:
            return "pending"

        if checkout.notified_at is not None:
            return "already_notified"

        buyer = await UserRepository(session).get_by_id(checkout.buyer_id)
        question = await QuestionRepository(session).get_with_users(
            checkout.question_id
        )
        if buyer is None or question is None:
            checkout.notification_error = "Buyer or question was not found"
            await session.commit()
            return "notification_failed"

        if buyer.id == question.recipient_id:
            target_user = question.sender
        elif buyer.id == question.sender_id:
            target_user = question.recipient
        else:
            checkout.notification_error = "Buyer is not a question participant"
            await session.commit()
            return "notification_failed"

        identity = await resolve_current_sender(bot, target_user)

        tracking = CrmTrackingService(session)
        await tracking.payment_succeeded(
            user_id=buyer.id,
            checkout_id=checkout.id,
        )
        await tracking.vip_activated(
            user_id=buyer.id,
            checkout_id=checkout.id,
        )
        await tracking.sender_revealed(
            user_id=buyer.id,
            question_id=question.id,
        )

        try:
            await bot.send_message(
                buyer.telegram_id,
                texts.VIP_ACTIVATED_WITH_SENDER.format(sender=identity.label),
            )
        except Exception as exc:
            checkout.notification_error = type(exc).__name__
            await session.commit()
            logger.exception(
                "Failed to send VIP activation notification",
                extra={"bot_code": instance.code, "telegram_user_id": buyer.telegram_id},
            )
            return "notification_failed"

        checkout.notified_at = datetime.now(timezone.utc)
        checkout.notification_error = None
        await session.commit()
        return "notified"
    finally:
        reset_current_bot(context_token)
        await bot.session.close()
