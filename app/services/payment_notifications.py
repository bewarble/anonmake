from __future__ import annotations

from datetime import datetime, timezone
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import texts
from app.models.reveal import RevealCheckout
from app.repositories import QuestionRepository, UserRepository
from app.services.impaya import ImpayaClient
from app.services.reveal_checkout import RevealCheckoutService
from app.services.sender_identity import resolve_current_sender
from app.services.crm_tracking import CrmTrackingService

logger = logging.getLogger(__name__)


async def finalize_checkout_and_notify(
    session: AsyncSession,
    bot: Bot,
    client: ImpayaClient,
    checkout: RevealCheckout,
    *,
    payment_form_url_template: str,
) -> str:
    paid = await RevealCheckoutService(
        session,
        client,
        payment_form_url_template=payment_form_url_template,
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

    identity = await resolve_current_sender(bot, question.sender)

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
            texts.VIP_ACTIVATED_WITH_SENDER.format(
                sender=identity.label
            ),
        )
    except Exception as exc:
        checkout.notification_error = str(exc)[:512]
        await session.commit()
        logger.exception("Failed to send VIP activation notification")
        return "notification_failed"

    checkout.notified_at = datetime.now(timezone.utc)
    checkout.notification_error = None
    await session.commit()
    return "notified"
