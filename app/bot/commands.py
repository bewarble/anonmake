from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand


PUBLIC_COMMANDS = (
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="cancel", description="Отключить автопродление"),
)


async def sync_public_commands(bot: Bot) -> None:
    """Keep Telegram's visible command list aligned with the public bot UX."""
    await bot.set_my_commands(list(PUBLIC_COMMANDS))
