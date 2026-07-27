from __future__ import annotations

from datetime import timedelta
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.payments import test_payment_keyboard
from app.core.config import load_settings
from app.repositories.users import UserRepository
from app.services.impaya import ImpayaClient
from app.services.subscription_checkout import SubscriptionCheckoutService

router = Router(name="payments")
logger = logging.getLogger(__name__)


def make_client(settings) -> ImpayaClient:
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


@router.message(Command("testpay"))
async def test_payment(
    message: Message,
    session: AsyncSession,
) -> None:
    if message.from_user is None:
        return

    settings = load_settings()
    if message.from_user.id not in settings.admin_ids_set:
        await message.answer("Команда недоступна")
        return

    if not settings.billing_enabled:
        await message.answer("BILLING_ENABLED=false")
        return

    if (
        not settings.impaya_api_token.strip()
        or not settings.public_base_url.strip()
        or not settings.impaya_payment_form_url_template.strip()
    ):
        await message.answer(
            "Платёжная конфигурация заполнена не полностью"
        )
        return

    user = await UserRepository(session).upsert_from_telegram(
        message.from_user
    )
    client = make_client(settings)

    try:
        payment_url, operation_id = await SubscriptionCheckoutService(
            session,
            client,
            payment_form_url_template=(
                settings.impaya_payment_form_url_template
            ),
            trial_amount=settings.trial_price_kopecks,
            trial_duration=timedelta(
                hours=settings.trial_duration_hours
            ),
        ).create_test_invoice(
            user_id=user.id,
            public_base_url=settings.public_base_url,
        )
    except Exception as exc:
        logger.exception("Test payment invoice creation failed")
        await message.answer(
            "Не удалось создать тестовый платёж.\n\n"
            f"Ошибка: {str(exc)[:300]}"
        )
        return
    finally:
        await client.close()

    await message.answer(
        "🧪 Тестовая подписка\n\n"
        "Списание: 1 ₽\n"
        "Доступ: 1 день\n"
        "После оплаты карта будет сохранена для "
        "рекуррентных списаний.\n\n"
        f"Операция: <code>{operation_id}</code>",
        reply_markup=test_payment_keyboard(payment_url),
    )
