from __future__ import annotations

from dataclasses import dataclass
import hmac

from fastapi import Request
from sqlalchemy import select

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.repositories.platform_admin import PlatformAdminRepository
from app.web.admin_auth import AdminAuth, password_fingerprint

COOKIE_NAME = "anonmake_admin_bot"
ALL_PROJECTS = "all"
auth = AdminAuth(load_settings())


@dataclass(slots=True, frozen=True)
class AdminBotScope:
    bots: tuple[BotInstance, ...]
    selected: BotInstance | None
    denied: bool = False

    @property
    def bot_id(self) -> int | None:
        return self.selected.id if self.selected is not None else None

    @property
    def code(self) -> str:
        return self.selected.code if self.selected is not None else ALL_PROJECTS

    @property
    def label(self) -> str:
        if self.selected is None:
            return "Все проекты"
        return self.selected.display_name or f"@{self.selected.username}"


async def load_admin_bot_scope(request: Request) -> AdminBotScope:
    requested = request.query_params.get("bot")
    if requested is None:
        requested = request.cookies.get(COOKIE_NAME, ALL_PROJECTS)
    requested = requested.strip().lower() or ALL_PROJECTS

    principal = auth.session_from_request(request)
    current_admin = None
    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        if principal is None:
            bots = list(
                (
                    await session.execute(
                        select(BotInstance)
                        .where(BotInstance.is_active.is_(True))
                        .order_by(BotInstance.id)
                    )
                ).scalars()
            )
        elif principal.admin_id is None:
            if await repo.admin_count() > 0:
                return AdminBotScope((), None, denied=True)
            bots = list(
                (
                    await session.execute(
                        select(BotInstance)
                        .where(BotInstance.is_active.is_(True))
                        .order_by(BotInstance.id)
                    )
                ).scalars()
            )
        else:
            current_admin = await repo.admin_by_id(principal.admin_id)
            if (
                current_admin is None
                or not current_admin.is_active
                or current_admin.role != principal.role
                or not hmac.compare_digest(
                    principal.credential_stamp,
                    password_fingerprint(current_admin.password_hash),
                )
            ):
                return AdminBotScope((), None, denied=True)
            bots = await repo.accessible_bots(current_admin)

    can_view_all = (
        principal is None
        or principal.admin_id is None
        or bool(current_admin and current_admin.is_superadmin)
    )

    if not can_view_all and requested == ALL_PROJECTS:
        selected = bots[0] if bots else None
        denied = not bots
    else:
        selected = next(
            (bot for bot in bots if bot.code == requested),
            None,
        )
        denied = requested != ALL_PROJECTS and selected is None

    return AdminBotScope(tuple(bots), selected, denied)
