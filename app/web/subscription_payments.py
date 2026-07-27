from __future__ import annotations

from datetime import timedelta

from aiogram import Bot
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.billing import Subscription
from app.repositories.users import UserRepository
from app.services.impaya import ImpayaClient
from app.services.subscription_checkout import SubscriptionCheckoutService

router = APIRouter(include_in_schema=False)
settings = load_settings()


def make_client() -> ImpayaClient:
    return ImpayaClient(
        settings.impaya_api_url,
        settings.impaya_api_token,
        (
            settings.impaya_binding_terminal_name
            or settings.impaya_terminal_name
        ),
        auth_header=settings.impaya_auth_header,
        auth_prefix=settings.impaya_auth_prefix,
        protocol_version=settings.impaya_protocol_version,
        recurrent_terminal_name=(
            settings.impaya_recurrent_terminal_name
            or settings.impaya_terminal_name
        ),
    )


async def finalize_subscription_payment(
    operation_id: str,
    *,
    notify: bool,
) -> str:
    client = make_client()
    bot = Bot(token=settings.require_bot_token()) if notify else None

    try:
        async with SessionFactory() as session:
            paid, attempt, newly_confirmed = await SubscriptionCheckoutService(
                session,
                client,
                payment_form_url_template=(
                    settings.impaya_payment_form_url_template
                ),
                trial_amount=settings.trial_price_kopecks,
                trial_duration=timedelta(
                    hours=settings.trial_duration_hours
                ),
            ).finalize(operation_id)

            if not paid or attempt is None:
                return "pending"

            if bot is not None and newly_confirmed:
                subscription = await session.get(
                    Subscription,
                    attempt.subscription_id,
                )
                if subscription is not None:
                    user = await UserRepository(session).get_by_id(
                        subscription.user_id
                    )
                    if user is not None:
                        await bot.send_message(
                            user.telegram_id,
                            "✅ Тестовая оплата подтверждена\n\n"
                            "VIP активирован на 1 день.\n"
                            "Карта сохранена для рекуррентных "
                            "списаний.",
                        )
            return "paid"
    finally:
        await client.close()
        if bot is not None:
            await bot.session.close()


@router.get(
    "/payments/subscription/success/{operation_id}",
    response_class=HTMLResponse,
)
async def subscription_success(operation_id: str) -> HTMLResponse:
    result = await finalize_subscription_payment(
        operation_id,
        notify=True,
    )
    if result == "paid":
        body = (
            "<h1>Оплата подтверждена</h1>"
            "<p>Подписка активирована. Можно вернуться в Telegram.</p>"
        )
    else:
        body = (
            "<h1>Платёж обрабатывается</h1>"
            "<p>Результат будет подтверждён через webhook "
            "или повторную проверку.</p>"
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
        "<h1>Оплата не завершена</h1>"
        "<p>Вернитесь в Telegram и повторите попытку.</p>"
        "</body></html>"
    )
