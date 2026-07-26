from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin import back_to_admin
from app.core.config import load_settings
from app.database.session import engine
from app.services.system_health import check_dependencies

router = Router(name="admin_system")


@router.callback_query(F.data == "admin:system")
async def admin_system_status(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    del session
    settings = load_settings()

    if (
        callback.from_user is None
        or callback.from_user.id not in settings.admin_ids_set
    ):
        await callback.answer("Недоступно", show_alert=True)
        return

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        status = await check_dependencies(engine, redis)
    finally:
        await redis.aclose()

    text = (
        "⚙️ Система\n\n"
        f"PostgreSQL: {'✅' if status.database else '❌'}\n"
        f"Redis: {'✅' if status.redis else '❌'}\n"
        f"Статус: {'работает' if status.healthy else 'есть проблема'}"
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=back_to_admin())
    await callback.answer()
