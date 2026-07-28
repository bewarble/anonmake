from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import select

from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance

COOKIE_NAME = "anonmake_admin_bot"
ALL_PROJECTS = "all"


@dataclass(slots=True, frozen=True)
class AdminBotScope:
    bots: tuple[BotInstance, ...]
    selected: BotInstance | None

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

    async with SessionFactory() as session:
        bots = tuple(
            (
                await session.execute(
                    select(BotInstance)
                    .where(BotInstance.is_active.is_(True))
                    .order_by(BotInstance.id)
                )
            ).scalars()
        )

    selected = next((bot for bot in bots if bot.code == requested), None)
    return AdminBotScope(bots=bots, selected=selected)
