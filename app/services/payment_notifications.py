from __future__ import annotations

from datetime import datetime, timezone
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reveal import RevealCheckout
from app.repositories import QuestionRepository, UserRepository
from app.services.impaya import ImpayaClient
from app.services.reveal_checkout import RevealCheckoutService

logger = logging.getLogger(__name__)


def sender_label(question) -> str:
    sender = question.sender
    if sender.username:
        return f"@{sender.username}"

    full_name = " ".join(
        part for part in (sender.first_name, sender.last_name) if part
    ).strip()
    if full_name:
        return f"{full_name}\nПубличный username отсутствует."
    return "Публичный username отсутствует."


async def finalize_checkout_and_notify(
    session: AsyncSession,
    bot: Bot,
    client: ImpayaClient,
    checkout: RevealCheckout,
    *,
    payment_form_url_template: str,
) -> str:
    """Reconcile with Impaya, activate VIP and notify the buyer.

    The incoming callback is never trusted as proof of payment. The final state
    is always fetched from Impaya by customer_operation_id.
    """
    paid = await RevealCheckoutService(
        session,
        client,
        payment_form_url_template=payment_form_url_template,
    ).finalize(checkout, user_id=checkout.buyer_id)

    if not paid:
        return "pending"

    # A completed checkout may be delivered more than once. notified_at makes
    # repeated callbacks harmless in the normal single-web-worker deployment.
    if checkout.notified_at is not None:
        return "already_notified"

    buyer = await UserRepository(session).get_by_id(checkout.buyer_id)
    question = await QuestionRepository(session).get_with_users(checkout.question_id)
    if buyer is None or question is None:
        checkout.notification_error = "Buyer or question was not found"
        await session.commit()
        return "notification_failed"

    try:
        await bot.send_message(
            buyer.telegram_id,
            "✅ VIP активирован на 1 день.\n\n"
            f"👤 Отправитель сообщения:\n\n{sender_label(question)}",
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
