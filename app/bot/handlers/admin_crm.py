from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.crm import crm_user_keyboard
from app.bot.states.crm import CrmNoteCreate, CrmTagCreate
from app.core.config import load_settings
from app.repositories.admin import AdminRepository
from app.repositories.crm import CrmRepository

router = Router(name="admin_crm")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


@router.callback_query(F.data.startswith("crm:user:"))
async def crm_user(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    try:
        user_id = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    profile = await CrmRepository(session).profile(user_id)

    tags = ", ".join(escape(tag.name) for tag in profile.tags) or "—"
    source = escape(profile.source.name) if profile.source else "Органика / неизвестно"

    notes = "\n".join(
        f"• {escape(note.text[:180])}" for note in profile.notes
    ) or "—"

    events = "\n".join(
        f"• {event.occurred_at:%d.%m} · {escape(event.summary[:140])}"
        for event in profile.events
    ) or "—"

    text = (
        "🗂 CRM-карточка\n\n"
        f"Пользователь ID: {user_id}\n"
        f"Источник: {source}\n"
        f"Теги: {tags}\n\n"
        f"📝 Заметки\n{notes}\n\n"
        f"🕘 Последние события\n{events}"
    )

    if callback.message:
        await callback.message.edit_text(
            text,
            reply_markup=crm_user_keyboard(user_id, profile.tags),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("crm:note:"))
async def crm_note_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    user_id = int((callback.data or "").rsplit(":", 1)[1])
    await state.set_state(CrmNoteCreate.waiting_text)
    await state.update_data(crm_user_id=user_id)
    if callback.message:
        await callback.message.answer("Введите заметку:")
    await callback.answer()


@router.message(CrmNoteCreate.waiting_text)
async def crm_note_save(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Заметка не может быть пустой")
        return
    if len(text) > 1000:
        await message.answer("Максимум 1000 символов")
        return

    data = await state.get_data()
    user_id = int(data["crm_user_id"])

    note = await CrmRepository(session).add_note(
        user_id=user_id,
        text=text,
        admin_telegram_id=message.from_user.id,
    )
    await AdminRepository(session).audit(
        admin_telegram_id=message.from_user.id,
        action="crm_add_note",
        target=str(user_id),
        details=f"note_id={note.id}",
    )
    await session.commit()
    await state.clear()
    await message.answer(
        "✅ Заметка сохранена",
        reply_markup=crm_user_keyboard(user_id, []),
    )


@router.callback_query(F.data.startswith("crm:tag:"))
async def crm_tag_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    user_id = int((callback.data or "").rsplit(":", 1)[1])
    await state.set_state(CrmTagCreate.waiting_name)
    await state.update_data(crm_user_id=user_id)
    if callback.message:
        await callback.message.answer("Введите название тега:")
    await callback.answer()


@router.message(CrmTagCreate.waiting_name)
async def crm_tag_save(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    name = " ".join((message.text or "").strip().split())
    if not name:
        await message.answer("Тег не может быть пустым")
        return

    data = await state.get_data()
    user_id = int(data["crm_user_id"])
    repository = CrmRepository(session)
    tag = await repository.ensure_tag(
        name=name,
        admin_telegram_id=message.from_user.id,
    )
    assigned = await repository.assign_tag(
        user_id=user_id,
        tag=tag,
        admin_telegram_id=message.from_user.id,
    )
    await AdminRepository(session).audit(
        admin_telegram_id=message.from_user.id,
        action="crm_assign_tag",
        target=str(user_id),
        details=f"tag={tag.name};assigned={assigned}",
    )
    await session.commit()
    await state.clear()
    await message.answer("✅ Тег добавлен")


@router.callback_query(F.data.startswith("crm:untag:"))
async def crm_untag(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    user_id = int(parts[2])
    tag_id = int(parts[3])
    removed = await CrmRepository(session).remove_tag(
        user_id=user_id,
        tag_id=tag_id,
    )
    await AdminRepository(session).audit(
        admin_telegram_id=callback.from_user.id,
        action="crm_remove_tag",
        target=str(user_id),
        details=f"tag_id={tag_id};removed={removed}",
    )
    await session.commit()
    await callback.answer("Тег удалён" if removed else "Тег уже удалён")
