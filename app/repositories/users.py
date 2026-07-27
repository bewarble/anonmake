from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_public_code(self, public_code: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.public_code == public_code)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _sync_telegram_fields(user: User, telegram_user: TelegramUser) -> None:
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_name = telegram_user.last_name

    async def get_or_create_from_telegram(
        self,
        telegram_user: TelegramUser,
    ) -> tuple[User, bool]:
        """Return a user and whether this call created the database record.

        The savepoint makes concurrent first /start updates safe: only the
        transaction that inserts the unique telegram_id receives created=True.
        """
        user = await self.get_by_telegram_id(telegram_user.id)
        if user is not None:
            self._sync_telegram_fields(user, telegram_user)
            await self.session.flush()
            return user, False

        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )

        try:
            async with self.session.begin_nested():
                self.session.add(user)
                await self.session.flush()
        except IntegrityError:
            user = await self.get_by_telegram_id(telegram_user.id)
            if user is None:
                raise
            self._sync_telegram_fields(user, telegram_user)
            await self.session.flush()
            return user, False

        return user, True

    async def upsert_from_telegram(self, telegram_user: TelegramUser) -> User:
        user, _ = await self.get_or_create_from_telegram(telegram_user)
        return user
