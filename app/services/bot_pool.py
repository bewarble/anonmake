from __future__ import annotations

import hashlib

from aiogram import Bot

from app.core.config import Settings
from app.models.bot_instance import BotInstance
from app.services.bot_credentials import resolve_bot_token


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class BotPool:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bots: dict[int, tuple[str, Bot]] = {}

    async def for_instance(self, session, instance: BotInstance) -> Bot:
        if not instance.is_active:
            raise RuntimeError(f"Bot instance is inactive: {instance.code}")

        token = await resolve_bot_token(session, self._settings, instance)
        fingerprint = _token_fingerprint(token)
        cached = self._bots.get(instance.id)
        if cached is not None:
            cached_fingerprint, bot = cached
            if cached_fingerprint == fingerprint:
                return bot
            # Admin token rotation must take effect without restarting the
            # delivery worker. Close the old HTTP session before replacing it.
            await bot.session.close()

        bot = Bot(token=token)
        self._bots[instance.id] = (fingerprint, bot)
        return bot

    async def close(self) -> None:
        for _, bot in self._bots.values():
            await bot.session.close()
        self._bots.clear()
