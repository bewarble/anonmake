from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_instance import BotInstance


class BotInstanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_code(self, code: str) -> BotInstance | None:
        return await self.session.scalar(
            select(BotInstance).where(BotInstance.code == code)
        )

    async def get_or_create(
        self,
        *,
        code: str,
        username: str,
        display_name: str,
    ) -> BotInstance:
        instance = await self.get_by_code(code)
        if instance is None:
            instance = BotInstance(
                code=code,
                username=username,
                display_name=display_name,
                is_active=True,
            )
            self.session.add(instance)
            await self.session.flush()
            return instance

        instance.username = username
        instance.display_name = display_name
        instance.is_active = True
        await self.session.flush()
        return instance
