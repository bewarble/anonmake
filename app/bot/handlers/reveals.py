from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reveals import reveal_checkout_keyboard
from app.core import texts
from app.core.config import load_settings
from app.repositories import QuestionRepository, UserRepository
from app.repositories.billing import BillingRepository
from app.repositories.reveals import RevealRepository
from app.services.impaya import ImpayaClient
from app.services.reveal_checkout import RevealCheckoutService
from app.services.vip import has_active_vip

router = Router(name="reveals")


def sender_label(question) -> str:
    sender = question.sender
    if sender.username:
        return f"@{sender.username}"

    full_name = " ".join(
        part for part in (sender.first_name, sender.last_name) if part
    ).strip()
    return full_name or "Username не указан"


def build_client(settings) -> ImpayaClient:
    return ImpayaClient(
        settings.impaya_api_url,
        settings.impaya_api_token,
        settings.impaya_terminal_name,
        auth_header=settings.impaya_auth_header,
        auth_prefix=settings.impaya_auth_prefix,
    )


@router.callback_query(F.data.startswith("reveal:"))
async def reveal_sender(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None:
        return

    try:
        question_id = int((callback.data or "").split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(texts.INVALID_LINK, show_alert=True)
        return

    buyer = await UserRepository(session).upsert_from_telegram(callback.from_user)
    question = await QuestionRepository(session).get_with_users(question_id)

    if question is None or question.recipient_id != buyer.id:
        await callback.answer(texts.ANSWER_NOT_FOUND, show_alert=True)
        return

    subscription = await BillingRepository(session).subscription_for_user(buyer.id)
    if has_active_vip(subscription):
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                texts.VIP_SENDER.format(sender=sender_label(question))
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
        ).create(
            checkout,
            user_id=buyer.id,
            success_url=success_url,
            fail_url=fail_url,
        )
    finally:
        await client.close()

    await callback.answer()
    if callback.message:
        await callback.message.answer(
            texts.VIP_OFFER,
            reply_markup=reveal_checkout_keyboard(
                payment_url=payment_url,
                offer_url=settings.offer_url,
            ),
        )
