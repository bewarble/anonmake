from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import main_menu_for
from app.bot.keyboards.subscriptions import cancel_subscription_keyboard
from app.repositories.billing import BillingRepository
from app.repositories.users import UserRepository

router = Router(name="subscriptions")


def format_until(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")


@router.message(StateFilter(None), Command("cancel"))
async def cancel_subscription_command(
    message: Message,
    session: AsyncSession,
) -> None:
    if message.from_user is None:
        return

    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer(
            "У вас нет действующей подписки.",
            reply_markup=main_menu_for(message.from_user.id),
        )
        return

    subscription = await BillingRepository(session).subscription_for_user(user.id)
    now = datetime.now(timezone.utc)

    if (
        subscription is None
        or subscription.access_until is None
        or subscription.access_until <= now
    ):
        await message.answer(
            "У вас нет действующей подписки.",
            reply_markup=main_menu_for(message.from_user.id),
        )
        return

    if not subscription.auto_renew:
        await message.answer(
            "Автопродление уже отключено.\n\n"
            f"Доступ сохранится до {format_until(subscription.access_until)}.",
            reply_markup=main_menu_for(message.from_user.id),
        )
        return

    await message.answer(
        "Вы действительно хотите отключить автоматическое продление?\n\n"
        "Подписка продолжит работать до конца оплаченного срока:\n"
        f"{format_until(subscription.access_until)}",
        reply_markup=cancel_subscription_keyboard(),
    )


@router.callback_query(F.data == "subscription:cancel:confirm")
async def cancel_subscription_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None:
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Подписка не найдена", show_alert=True)
        return

    repository = BillingRepository(session)
    subscription = await repository.subscription_for_user(user.id)
    now = datetime.now(timezone.utc)

    if (
        subscription is None
        or subscription.access_until is None
        or subscription.access_until <= now
    ):
        await callback.answer("Действующей подписки нет", show_alert=True)
        return

    await repository.cancel_auto_renew(
        subscription,
        cancelled_at=now,
    )
    await session.commit()

    if callback.message:
        await callback.message.edit_text(
            "✅ Автопродление отключено.\n\n"
            "Подписка продолжит работать до:\n"
            f"{format_until(subscription.access_until)}"
        )
    await callback.answer()


@router.callback_query(F.data == "subscription:cancel:keep")
async def cancel_subscription_keep(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Автопродление оставлено включённым."
        )
    await callback.answer()
