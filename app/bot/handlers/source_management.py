from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.source_admin import source_delete_confirm_keyboard
from app.core.config import load_settings
from app.core import admin_texts
from app.repositories.admin import AdminRepository
from app.repositories.marketing_cleanup import MarketingCleanupRepository

router = Router(name="source_management")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


@router.callback_query(F.data.in_({"admin25:cancel:export", "admin25:referrals:cancel"}))
async def cancel_admin_section(callback: CallbackQuery) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    if callback.message:
        await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "source:create:cancel")
async def cancel_source_create(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text(admin_texts.SOURCE_CREATE_CANCELLED)
    await callback.answer()


@router.callback_query(F.data.startswith("source:delete:"))
async def request_source_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    try:
        source_id = int((callback.data or "").rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(admin_texts.INVALID_DATA, show_alert=True)
        return
    source = await MarketingCleanupRepository(session).source(source_id)
    if source is None:
        await callback.answer(admin_texts.SOURCE_NOT_FOUND, show_alert=True)
        return
    if callback.message:
        await callback.message.edit_text(
            admin_texts.SOURCE_DELETE_PROMPT.format(name=escape(source.name)),
            reply_markup=source_delete_confirm_keyboard(source.id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("source:delete_confirm:"))
async def confirm_source_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer(admin_texts.DENIED, show_alert=True)
        return
    try:
        source_id = int((callback.data or "").rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(admin_texts.INVALID_DATA, show_alert=True)
        return
    deleted = await MarketingCleanupRepository(session).delete_source(source_id)
    if deleted:
        await AdminRepository(session).audit(
            admin_telegram_id=callback.from_user.id,
            action="archive_traffic_source",
            target=str(source_id),
        )
        await session.commit()
    if callback.message:
        await callback.message.edit_text(
            admin_texts.SOURCE_DELETED if deleted else admin_texts.SOURCE_ALREADY_DELETED
        )
    await callback.answer()
