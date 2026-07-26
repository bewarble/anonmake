from __future__ import annotations

from datetime import timezone
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin import admin_menu, back_to_admin, user_actions
from app.bot.keyboards.admin_bi import admin_reply_menu
from app.bot.states.admin import AdminLookup
from app.core.config import load_settings
from app.repositories.admin import AdminRepository

router = Router(name="admin")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


async def reject_message(message: Message) -> None:
    await message.answer("Команда недоступна")


async def reject_callback(callback: CallbackQuery) -> None:
    await callback.answer("Недоступно", show_alert=True)


def dashboard_text(data: dict[str, int]) -> str:
    return (
        "🛠 Админ-панель\n\n"
        f"Пользователи: {data['users']:,}\n"
        f"Новые за 24 ч: {data['new_users_24h']:,}\n\n"
        f"Сообщения: {data['questions']:,}\n"
        f"Новые за 24 ч: {data['new_questions_24h']:,}\n"
        f"Ответы: {data['answers']:,}\n\n"
        f"Активный VIP: {data['vip']:,}"
    ).replace(",", " ")


async def show_dashboard(
    session: AsyncSession,
    *,
    message: Message | None = None,
    callback: CallbackQuery | None = None,
) -> None:
    data = await AdminRepository(session).dashboard()
    text = dashboard_text(data)

    if callback and callback.message:
        try:
            await callback.message.edit_text(
                text,
                reply_markup=admin_menu(),
            )
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc):
                raise

        await callback.answer()
        return

    if message:
        await message.answer(
            text,
            reply_markup=admin_menu(),
        )
        await message.answer(
            "Быстрое меню",
            reply_markup=admin_reply_menu(),
        )


@router.message(Command("admin"))
async def admin_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await reject_message(message)
        return
    await show_dashboard(session, message=message)


@router.callback_query(F.data == "admin:home")
async def admin_home(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await reject_callback(callback)
        return
    await show_dashboard(session, callback=callback)


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await reject_callback(callback)
        return

    data = await AdminRepository(session).dashboard()
    text = (
        "📊 Статистика\n\n"
        f"Всего пользователей: {data['users']:,}\n"
        f"Новых за 24 ч: {data['new_users_24h']:,}\n\n"
        f"Всего сообщений: {data['questions']:,}\n"
        f"Новых за 24 ч: {data['new_questions_24h']:,}\n"
        f"Ответов: {data['answers']:,}\n\n"
        f"Активных VIP: {data['vip']:,}"
    ).replace(",", " ")
    if callback.message:
        await callback.message.edit_text(text, reply_markup=back_to_admin())
    await callback.answer()


@router.callback_query(F.data == "admin:payments")
async def admin_payments(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await reject_callback(callback)
        return

    data = await AdminRepository(session).payments()
    rubles = data["success_amount_kopecks"] / 100
    text = (
        "💳 Платежи\n\n"
        f"Успешных: {data['success_count']:,}\n"
        f"Сумма: {rubles:,.2f} ₽\n"
        f"Ошибок: {data['failed_count']:,}\n"
        f"Ожидают: {data['pending_count']:,}"
    ).replace(",", " ")
    if callback.message:
        await callback.message.edit_text(text, reply_markup=back_to_admin())
    await callback.answer()


@router.callback_query(F.data == "admin:find")
async def admin_find(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await reject_callback(callback)
        return

    await state.set_state(AdminLookup.waiting_for_user)
    if callback.message:
        await callback.message.answer(
            "🔎 Отправьте Telegram ID, внутренний ID или @username"
        )
    await callback.answer()


@router.message(AdminLookup.waiting_for_user, F.text)
async def admin_find_result(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        await reject_message(message)
        return

    query = (message.text or "").strip()
    user = await AdminRepository(session).find_user(query)
    await state.clear()

    if user is None:
        await message.answer("Пользователь не найден", reply_markup=admin_menu())
        return

    subscription = await AdminRepository(session).subscription_for_user(user.id)
    username = f"@{escape(user.username)}" if user.username else "—"
    vip_until = "нет"
    if subscription and subscription.access_until:
        value = subscription.access_until
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        vip_until = value.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    text = (
        "👤 Пользователь\n\n"
        f"ID: {user.id}\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Username: {username}\n"
        f"Имя: {escape(user.first_name or '—')}\n"
        f"VIP до: {vip_until}"
    )
    await message.answer(text, reply_markup=user_actions(user.id))


@router.callback_query(F.data.startswith("admin:vip:"))
async def admin_grant_vip(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await reject_callback(callback)
        return

    try:
        _, _, user_id_raw, days_raw = (callback.data or "").split(":")
        user_id = int(user_id_raw)
        days = int(days_raw)
    except (ValueError, AttributeError):
        await callback.answer("Некорректные данные", show_alert=True)
        return

    repo = AdminRepository(session)
    subscription = await repo.grant_vip(user_id, days)
    await repo.audit(
        admin_telegram_id=callback.from_user.id,
        action="grant_vip",
        target=str(user_id),
        details=f"days={days}; access_until={subscription.access_until}",
    )
    await session.commit()
    await callback.answer(f"VIP продлён на {days} дн.", show_alert=True)


@router.callback_query(F.data.startswith("admin:vip_revoke:"))
async def admin_revoke_vip(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await reject_callback(callback)
        return

    try:
        user_id = int((callback.data or "").rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректные данные", show_alert=True)
        return

    repo = AdminRepository(session)
    await repo.revoke_vip(user_id)
    await repo.audit(
        admin_telegram_id=callback.from_user.id,
        action="revoke_vip",
        target=str(user_id),
    )
    await session.commit()
    await callback.answer("VIP отключён", show_alert=True)


@router.callback_query(F.data == "admin:audit")
async def admin_audit(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await reject_callback(callback)
        return

    items = await AdminRepository(session).recent_audit(limit=10)
    if not items:
        text = "🧾 Журнал пуст"
    else:
        rows = ["🧾 Последние действия\n"]
        for item in items:
            created = item.created_at.strftime("%d.%m %H:%M")
            rows.append(
                f"{created} · {item.action} · {item.target or '—'}"
            )
        text = "\n".join(rows)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=back_to_admin())
    await callback.answer()
