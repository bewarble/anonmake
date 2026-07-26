from __future__ import annotations

from dataclasses import dataclass
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SenderIdentity:
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None

    @property
    def label(self) -> str:
        if self.username:
            return f"@{self.username}"

        full_name = " ".join(
            value
            for value in (self.first_name, self.last_name)
            if value
        ).strip()
        return full_name or "Имя не указано"


async def resolve_current_sender(
    bot: Bot,
    sender,
) -> SenderIdentity:
    """Resolve sender data at the exact moment of disclosure.

    Telegram's current private-chat data is preferred. The stored database
    profile is only a fallback when Telegram cannot return the chat.
    """

    try:
        chat = await bot.get_chat(sender.telegram_id)
    except TelegramAPIError:
        logger.info(
            "Could not refresh sender profile from Telegram",
            extra={"telegram_user_id": sender.telegram_id},
        )
        return SenderIdentity(
            telegram_id=sender.telegram_id,
            username=sender.username,
            first_name=sender.first_name,
            last_name=sender.last_name,
        )

    return SenderIdentity(
        telegram_id=sender.telegram_id,
        username=chat.username,
        first_name=chat.first_name,
        last_name=chat.last_name,
    )
