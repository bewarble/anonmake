from __future__ import annotations

from datetime import timedelta

from aiogram import Bot
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core import texts
from app.core.bot_context import CurrentBot, reset_current_bot, set_current_bot
from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.billing import PaymentAttempt, Subscription
from app.models.bot_instance import BotInstance
from app.repositories.users import UserRepository
from app.services.bot_credentials import resolve_bot_token
from app.services.impaya_factory import create_impaya_client, load_impaya_config
from app.services.subscription_checkout import SubscriptionCheckoutService

router = APIRouter(include_in_schema=False)
settings = load_settings()


async def finalize_subscription_payment(
    operation_id: str,
    *,
    notify: bool,
) -> str:
    bot: Bot | None = None
    client = None
    context_token = None

    try:
        async with SessionFactory() as session:
            # Operation IDs are globally unique. Resolve project ownership first;
            # only then load that project's payment gateway and bot credentials.
            seed_attempt = await session.scalar(
                select(PaymentAttempt).where(
                    PaymentAttempt.customer_operation_id == operation_id
                )
            )
            if seed_attempt is None:
                return "pending"

            instance = await session.get(BotInstance, seed_attempt.bot_id)
            if instance is None:
                return "pending"

            context_token = set_current_bot(
                CurrentBot(
                    instance.id,
                    instance.code,
                    instance.username,
                    instance.display_name,
                )
            )
            impaya_config = await load_impaya_config(session, settings, instance.id)
            client = create_impaya_client(impaya_config)

            paid, attempt, newly_confirmed = await SubscriptionCheckoutService(
                session,
                client,
                payment_form_url_template=impaya_config.payment_form_url_template,
                trial_amount=settings.trial_price_kopecks,
                trial_duration=timedelta(hours=settings.trial_duration_hours),
            ).finalize(operation_id)

            if not paid or attempt is None:
                return "pending"

            if notify and newly_confirmed:
                token = await resolve_bot_token(session, settings, instance)
                bot = Bot(token=token)
                subscription = await session.get(
                    Subscription,
                    attempt.subscription_id,
                )
                if (
                    subscription is not None
                    and subscription.bot_id == instance.id
                ):
                    user = await UserRepository(session).get_by_id(
                        subscription.user_id
                    )
                    if user is not None:
                        await bot.send_message(
                            user.telegram_id,
                            texts.ACCESS_ACTIVE,
                        )
            return "paid"
    finally:
        if context_token is not None:
            reset_current_bot(context_token)
        if client is not None:
            await client.close()
        if bot is not None:
            await bot.session.close()


@router.get(
    "/payments/subscription/success/{operation_id}",
    response_class=HTMLResponse,
)
async def subscription_success(operation_id: str) -> HTMLResponse:
    result = await finalize_subscription_payment(operation_id, notify=True)
    if result == "paid":
        body = (
            "<h1>✅ Всё готово!</h1>"
            "<p>Вернитесь в Telegram — VIP статус уже активирован.</p>"
        )
    else:
        body = (
            "<h1>Платёж обрабатывается</h1>"
            "<p>Результат будет подтверждён автоматически.</p>"
        )

    return HTMLResponse(
        "<!doctype html><html lang='ru'><meta charset='utf-8'>"
        "<title>AnonMake</title><body>"
        f"{body}</body></html>"
    )


@router.get(
    "/payments/subscription/fail/{operation_id}",
    response_class=HTMLResponse,
)
async def subscription_fail(operation_id: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html lang='ru'><meta charset='utf-8'>"
        "<title>AnonMake</title><body>"
        "<h1>❌ Оплата не завершена</h1>"
        "<p>Вернитесь в Telegram и попробуйте ещё раз.</p>"
        "</body></html>"
    )
