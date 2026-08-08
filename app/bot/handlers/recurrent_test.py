from __future__ import annotations

from datetime import timedelta
from html import escape
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.recurrent_test import recurrent_test_confirm, recurrent_test_menu
from app.core.config import load_settings
from app.repositories.billing import BillingRepository
from app.repositories.users import UserRepository
from app.services.billing import BillingService, ChargeDecision
from app.services.impaya_factory import create_impaya_client, load_impaya_config

router = Router(name="recurrent_test")
logger = logging.getLogger(__name__)


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


async def payment_context(session: AsyncSession, telegram_id: int):
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if user is None:
        return None, None
    repository = BillingRepository(session)
    return (
        await repository.subscription_for_user(user.id),
        await repository.payment_method_for_user(user.id),
    )


@router.message(Command("testcharge"))
async def testcharge_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    subscription, method = await payment_context(session, message.from_user.id)
    if (
        subscription is None
        or method is None
        or not method.binding_id
        or not method.impaya_user_id
        or not method.is_active
        or not method.is_recurrent
    ):
        await message.answer(
            "Сначала выполните /testpay и успешно привяжите карту."
        )
        return

    await message.answer(
        "🧪 Тест MIT-списания\n\n"
        f"Карта: {method.masked_pan or 'привязана'}\n"
        "Выберите сумму:",
        reply_markup=recurrent_test_menu(),
    )


@router.callback_query(F.data == "billingtest:choose:primary")
async def choose_primary(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    if callback.message:
        await callback.message.edit_text(
            "Подтвердите реальное тестовое списание 299 ₽. "
            "При успехе будет добавлено 3 дня.",
            reply_markup=recurrent_test_confirm("primary", "299"),
        )
    await callback.answer()


@router.callback_query(F.data == "billingtest:choose:fallback")
async def choose_fallback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    if callback.message:
        await callback.message.edit_text(
            "Подтвердите реальное тестовое списание 99 ₽. "
            "При успехе будет добавлен 1 день.",
            reply_markup=recurrent_test_confirm("fallback", "99"),
        )
    await callback.answer()


@router.callback_query(F.data == "billingtest:back")
async def go_back(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Выберите сумму:",
            reply_markup=recurrent_test_menu(),
        )
    await callback.answer()


@router.callback_query(F.data == "billingtest:cancel")
async def cancel_test(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text("Тестовое списание отменено.")
    await callback.answer()


@router.callback_query(F.data.startswith("billingtest:confirm:"))
async def confirm_test_charge(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if not is_admin(callback.from_user.id):
        return

    kind = (callback.data or "").rsplit(":", 1)[-1]
    settings = load_settings()
    subscription, method = await payment_context(
        session,
        callback.from_user.id,
    )
    if subscription is None or method is None:
        await callback.answer("Нет подписки или карты", show_alert=True)
        return

    if kind == "primary":
        amount = settings.primary_price_kopecks
        period = timedelta(days=settings.primary_duration_days)
        attempt_kind = "test_primary"
    elif kind == "fallback":
        amount = settings.fallback_price_kopecks
        period = timedelta(days=settings.fallback_duration_days)
        attempt_kind = "test_fallback"
    else:
        await callback.answer("Неизвестный тест", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text("⏳ Отправляю MIT-запрос…")
    await callback.answer()

    impaya_config = await load_impaya_config(
        session,
        settings,
        subscription.bot_id,
    )
    client = create_impaya_client(impaya_config)
    try:
        result = await BillingService(
            session,
            client,
            primary_amount=settings.primary_price_kopecks,
            primary_duration=timedelta(
                days=settings.primary_duration_days
            ),
            fallback_amount=settings.fallback_price_kopecks,
            fallback_duration=timedelta(
                days=settings.fallback_duration_days
            ),
        ).test_charge(
            subscription,
            method,
            amount=amount,
            access_period=period,
            kind=attempt_kind,
        )
    except Exception as exc:
        await session.rollback()
        logger.exception("Test recurrent charge failed")
        if callback.message:
            await callback.message.edit_text(
                "❌ Ошибка тестового списания:\n\n"
                f"{str(exc)[:400]}"
            )
        return
    finally:
        await client.close()

    if result.decision == ChargeDecision.SUCCESS:
        text = (
            f"✅ Списание {amount / 100:.2f} ₽ успешно.\n\n"
            f"Attempt: {result.attempt.id}\n"
            f"Operation: <code>{escape(result.attempt.customer_operation_id)}</code>\n"
            f"VIP статус активен до: {result.access_until}"
        )
    elif result.decision == ChargeDecision.INSUFFICIENT:
        text = (
            "⚠️ Недостаточно средств.\n\n"
            f"Код: {result.attempt.error_code or '—'}"
        )
    elif result.decision == ChargeDecision.PENDING:
        text = (
            "⏳ Неопределённый результат.\n\n"
            "Второе списание не запускается до уточнения статуса."
        )
    else:
        text = (
            "❌ Списание отклонено.\n\n"
            f"Код: {result.attempt.error_code or '—'}\n"
            f"Описание: {result.attempt.error_message or '—'}"
        )

    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode=(
                "HTML"
                if result.decision == ChargeDecision.SUCCESS
                else None
            ),
        )
