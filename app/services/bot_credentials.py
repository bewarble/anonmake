from __future__ import annotations

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.platform_security import decrypt_secret
from app.models.bot_instance import BotInstance


def token_hint(token: str) -> str:
    if len(token) < 12:
        return "••••••••"
    return f"{token[:6]}••••••{token[-4:]}"


async def resolve_bot_token(
    session: AsyncSession,
    settings: Settings,
    instance: BotInstance,
) -> str:
    if instance.token_encrypted:
        return decrypt_secret(instance.token_encrypted, settings.web_admin_secret)
    token = settings.bot_tokens().get(instance.code)
    if not token:
        raise RuntimeError(f"Для проекта {instance.code} не задан Telegram-токен")
    return token


async def verify_telegram_token(token: str):
    bot = Bot(token=token)
    try:
        return await bot.get_me()
    finally:
        await bot.session.close()
