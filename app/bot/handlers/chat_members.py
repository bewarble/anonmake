from __future__ import annotations

from aiogram import Router
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import UserRepository

router = Router(name="chat_members")

BLOCKED_STATUSES = {"kicked", "left"}
ALIVE_STATUSES = {"member", "administrator", "creator", "restricted"}


def enum_value(value) -> str:
    return str(getattr(value, "value", value))


@router.my_chat_member()
async def track_private_bot_membership(
    event: ChatMemberUpdated,
    session: AsyncSession,
) -> None:
    """Keep the user's live/dead state synchronized with Telegram.

    In a private chat Telegram reports the bot as ``kicked`` when the user
    blocks it and ``member`` again after the user unblocks/returns.
    """
    if enum_value(event.chat.type) != "private":
        return

    status = enum_value(event.new_chat_member.status)
    if status in BLOCKED_STATUSES:
        await UserRepository(session).set_block_state(
            event.chat.id,
            is_blocked=True,
            changed_at=event.date,
        )
    elif status in ALIVE_STATUSES:
        await UserRepository(session).set_block_state(
            event.chat.id,
            is_blocked=False,
            changed_at=event.date,
        )
