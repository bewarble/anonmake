from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import main_menu_for
from app.bot.keyboards.subscriptions import cancel_subscription_keyboard
from app.core import texts
from app.repositories.billing import BillingRepository
from app.repositories.users import UserRepository

router = Router(name="subscriptions")


async def _safe_edit(callback: CallbackQuery, text: str) -> None:
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


@router.message(Command("cancel"))
async def cancel_subscription_command(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """`/cancel` is reserved exclusively for disabling subscription auto-renewal."""
    if message.from_user is None:
        return

    # Do not let the literal command become question/answer content when a user
    # happens to invoke it while an input FSM is active.
    await state.clear()

    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer(
            texts.NO_ACTIVE_ACCESS,
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
            texts.NO_ACTIVE_ACCESS,
            reply_markup=main_menu_for(message.from_user.id),
        )
        return

    if not subscription.auto_renew:
        await message.answer(
            texts.AUTO_RENEW_ALREADY_OFF,
            reply_markup=main_menu_for(message.from_user.id),
        )
        return

    await message.answer(
        texts.AUTO_RENEW_CONFIRM,
        reply_markup=cancel_subscription_keyboard(),
    )


@router.callback_query(F.data == "subscription:cancel:confirm")
async def cancel_subscription_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(texts.NO_ACTIVE_ACCESS, show_alert=True)
        return

    repository = BillingRepository(session)
    subscription = await repository.subscription_for_user(user.id)
    now = datetime.now(timezone.utc)

    if (
        subscription is None
        or subscription.access_until is None
        or subscription.access_until <= now
    ):
        await callback.answer(texts.NO_ACTIVE_ACCESS, show_alert=True)
        return

    if not subscription.auto_renew:
        await _safe_edit(callback, texts.AUTO_RENEW_OFF)
        await callback.answer(texts.AUTO_RENEW_ALREADY_OFF)
        return

    await repository.cancel_auto_renew(subscription, cancelled_at=now)
    await session.commit()
    await _safe_edit(callback, texts.AUTO_RENEW_OFF)
    await callback.answer()


@router.callback_query(F.data == "subscription:cancel:keep")
async def cancel_subscription_keep(callback: CallbackQuery) -> None:
    await _safe_edit(callback, texts.AUTO_RENEW_KEEP)
    await callback.answer()
