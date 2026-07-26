from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_delivery import (
    delivery_dashboard_keyboard,
    failed_deliveries_keyboard,
)
from app.core.config import load_settings
from app.repositories.admin import AdminRepository
from app.repositories.delivery_admin import DeliveryAdminRepository

router = Router(name="admin_delivery")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


async def safe_edit(callback: CallbackQuery, text: str, reply_markup) -> None:
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


@router.callback_query(F.data == "admin:delivery")
async def delivery_dashboard(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    data = await DeliveryAdminRepository(session).summary()
    text = (
        "📨 Доставка\n\n"
        f"В очереди: {data['pending']}\n"
        f"Обрабатываются: {data['processing']}\n"
        f"Повтор: {data['retry']}\n"
        f"Доставлено: {data['delivered']}\n"
        f"Ошибки: {data['failed']}"
    )
    await safe_edit(callback, text, delivery_dashboard_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:delivery:failed")
async def delivery_failed(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    jobs = await DeliveryAdminRepository(session).recent_failed(limit=10)
    if not jobs:
        text = "✅ Ошибок доставки нет"
        ids: list[int] = []
    else:
        rows = ["❌ Последние ошибки"]
        for job in jobs:
            error = escape((job.last_error or "Без описания")[:120])
            rows.append(
                f"#{job.id} · {job.kind} · chat {job.chat_id}\n{error}"
            )
        text = "\n\n".join(rows)
        ids = [job.id for job in jobs]

    await safe_edit(callback, text, failed_deliveries_keyboard(ids))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delivery:retry:"))
async def delivery_retry(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    try:
        delivery_id = int((callback.data or "").rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный ID", show_alert=True)
        return

    repository = DeliveryAdminRepository(session)
    retried = await repository.retry_failed(delivery_id)

    await AdminRepository(session).audit(
        admin_telegram_id=callback.from_user.id,
        action="retry_delivery",
        target=str(delivery_id),
        details=f"retried={retried}",
    )
    await session.commit()

    if retried:
        await callback.answer("Задача возвращена в очередь", show_alert=True)
    else:
        await callback.answer(
            "Задача не найдена или уже обрабатывается",
            show_alert=True,
        )
