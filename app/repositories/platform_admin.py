from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_instance import BotInstance
from app.models.platform_admin import (
    AdminProjectAccess,
    AdminUser,
    PaymentGatewayConfig,
)


class PlatformAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def admin_by_email(self, email: str) -> AdminUser | None:
        return await self.session.scalar(
            select(AdminUser).where(
                AdminUser.email == email.strip().lower(),
                AdminUser.is_active.is_(True),
            )
        )

    async def admin_by_id(self, admin_id: int) -> AdminUser | None:
        return await self.session.scalar(
            select(AdminUser).where(AdminUser.id == admin_id)
        )

    async def list_admins(self) -> list[AdminUser]:
        return list(
            (
                await self.session.execute(
                    select(AdminUser).order_by(AdminUser.id)
                )
            ).scalars()
        )

    async def create_admin(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str,
        role: str,
        bot_ids: list[int],
    ) -> AdminUser:
        item = AdminUser(
            email=email.strip().lower(),
            display_name=display_name.strip(),
            password_hash=password_hash,
            role=role,
        )
        self.session.add(item)
        await self.session.flush()
        await self.set_access(item.id, bot_ids)
        await self.session.commit()
        return item

    async def set_access(self, admin_id: int, bot_ids: list[int]) -> None:
        await self.session.execute(
            delete(AdminProjectAccess).where(
                AdminProjectAccess.admin_user_id == admin_id
            )
        )
        for bot_id in sorted(set(bot_ids)):
            self.session.add(
                AdminProjectAccess(admin_user_id=admin_id, bot_id=bot_id)
            )

    async def accessible_bots(self, admin: AdminUser) -> list[BotInstance]:
        statement = select(BotInstance).order_by(BotInstance.id)
        if not admin.is_superadmin:
            statement = statement.join(
                AdminProjectAccess,
                AdminProjectAccess.bot_id == BotInstance.id,
            ).where(AdminProjectAccess.admin_user_id == admin.id)
        return list((await self.session.execute(statement)).scalars())

    async def mark_login(self, admin: AdminUser) -> None:
        admin.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def gateway_for_bot(
        self, bot_id: int, provider: str = "impaya"
    ) -> PaymentGatewayConfig | None:
        return await self.session.scalar(
            select(PaymentGatewayConfig).where(
                PaymentGatewayConfig.bot_id == bot_id,
                PaymentGatewayConfig.provider == provider,
                PaymentGatewayConfig.is_active.is_(True),
            )
        )

    async def upsert_gateway(
        self,
        *,
        bot_id: int,
        provider: str,
        values: dict,
    ) -> PaymentGatewayConfig:
        item = await self.session.scalar(
            select(PaymentGatewayConfig).where(
                PaymentGatewayConfig.bot_id == bot_id,
                PaymentGatewayConfig.provider == provider,
            )
        )
        if item is None:
            item = PaymentGatewayConfig(
                bot_id=bot_id,
                provider=provider,
                **values,
            )
            self.session.add(item)
        else:
            for key, value in values.items():
                setattr(item, key, value)
        await self.session.commit()
        return item
