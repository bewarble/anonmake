from __future__ import annotations

from datetime import datetime, timezone

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.user import User, UserPublicCodeAlias, generate_public_code


PUBLIC_CODE_CREATE_ATTEMPTS = 20


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        bot_id = require_current_bot().id
        result = await self.session.execute(
            select(User).where(
                User.id == user_id,
                User.bot_id == bot_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        bot_id = require_current_bot().id
        result = await self.session.execute(
            select(User).where(
                User.bot_id == bot_id,
                User.telegram_id == telegram_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_public_code(self, public_code: str) -> User | None:
        bot_id = require_current_bot().id
        user = await self.session.scalar(
            select(User).where(
                User.bot_id == bot_id,
                User.public_code == public_code,
            )
        )
        if user is not None:
            return user
        return await self.session.scalar(
            select(User)
            .join(UserPublicCodeAlias, UserPublicCodeAlias.user_id == User.id)
            .where(
                User.bot_id == bot_id,
                UserPublicCodeAlias.bot_id == bot_id,
                UserPublicCodeAlias.public_code == public_code,
            )
        )

    @staticmethod
    def _sync_telegram_fields(user: User, telegram_user: TelegramUser) -> None:
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_name = telegram_user.last_name
        # Any real interaction proves the user can currently reach the bot.
        user.is_blocked = False
        user.updated_at = datetime.now(timezone.utc)

    async def set_block_state(
        self,
        telegram_id: int,
        *,
        is_blocked: bool,
        changed_at: datetime | None = None,
    ) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        moment = changed_at or datetime.now(timezone.utc)
        user.is_blocked = is_blocked
        if is_blocked:
            user.blocked_at = moment
        else:
            user.updated_at = moment
        await self.session.flush()
        return user

    async def get_or_create_from_telegram(
        self,
        telegram_user: TelegramUser,
    ) -> tuple[User, bool]:
        """Return a user and whether this call created the database record.

        Concurrent first interactions and short public-code collisions are both
        handled through savepoints. Existing users are always marked alive.
        """
        user = await self.get_by_telegram_id(telegram_user.id)
        if user is not None:
            self._sync_telegram_fields(user, telegram_user)
            await self.session.flush()
            return user, False

        bot_id = require_current_bot().id
        for _ in range(PUBLIC_CODE_CREATE_ATTEMPTS):
            user = User(
                bot_id=bot_id,
                telegram_id=telegram_user.id,
                public_code=generate_public_code(),
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                is_blocked=False,
            )
            alias_owner = await self.session.scalar(
                select(UserPublicCodeAlias.user_id).where(
                    UserPublicCodeAlias.bot_id == bot_id,
                    UserPublicCodeAlias.public_code == user.public_code,
                )
            )
            if alias_owner is not None:
                continue
            try:
                async with self.session.begin_nested():
                    self.session.add(user)
                    await self.session.flush()
            except IntegrityError:
                existing = await self.get_by_telegram_id(telegram_user.id)
                if existing is not None:
                    self._sync_telegram_fields(existing, telegram_user)
                    await self.session.flush()
                    return existing, False
                # The telegram id is still free, so this was most likely a
                # public-code collision. Generate another short code.
                continue
            return user, True

        raise RuntimeError("Could not allocate a unique public code")

    async def upsert_from_telegram(self, telegram_user: TelegramUser) -> User:
        user, _ = await self.get_or_create_from_telegram(telegram_user)
        return user
