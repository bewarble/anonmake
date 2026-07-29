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


async def fetch_bot_avatar(token: str, bot_id: int) -> tuple[bytes, str] | None:
    """Return the current Telegram bot avatar without exposing its token."""
    from io import BytesIO

    bot = Bot(token=token)
    try:
        photos = await bot.get_user_profile_photos(user_id=bot_id, limit=1)
        if not photos.photos or not photos.photos[0]:
            return None
        largest = photos.photos[0][-1]
        file = await bot.get_file(largest.file_id)
        if not file.file_path:
            return None
        buffer = BytesIO()
        await bot.download_file(file.file_path, destination=buffer)
        return buffer.getvalue(), "image/jpeg"
    finally:
        await bot.session.close()
