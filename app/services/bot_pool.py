from __future__ import annotations

from aiogram import Bot

from app.core.config import Settings
from app.models.bot_instance import BotInstance


class BotPool:
    def __init__(self, settings: Settings) -> None:
        self._tokens = settings.bot_tokens()
        self._bots: dict[str, Bot] = {}

    def for_instance(self, instance: BotInstance) -> Bot:
        if not instance.is_active:
            raise RuntimeError(f"Bot instance is inactive: {instance.code}")

        token = self._tokens.get(instance.code)
        if not token:
            raise RuntimeError(
                f"No Telegram token configured for bot code: {instance.code}"
            )

        bot = self._bots.get(instance.code)
        if bot is None:
            bot = Bot(token=token)
            self._bots[instance.code] = bot
        return bot

    async def close(self) -> None:
        for bot in self._bots.values():
            await bot.session.close()
        self._bots.clear()
