from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.models.billing import PaymentAttempt, Subscription
from app.models.delivery import DeliveryOutbox
from app.models.user import User
from app.web.admin import login_redirect, page_context, require_session, templates

router = APIRouter(prefix="/admin", include_in_schema=False)
SUCCESS = ("success", "paid", "completed")


@dataclass(slots=True, frozen=True)
class ProjectRow:
    bot: BotInstance
    users: int
    active_vip: int
    revenue_kopecks: int
    delivered: int
    pending: int
    failed: int
    last_delivery_at: datetime | None

    @property
    def delivery_health(self) -> str:
        if self.failed:
            return "warning"
        if self.pending:
            return "pending"
        return "healthy"


async def project_rows() -> list[ProjectRow]:
    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        bots = (
            await session.execute(
                select(BotInstance).order_by(BotInstance.id)
            )
        ).scalars().all()
        rows: list[ProjectRow] = []
        for bot in bots:
            users = int(await session.scalar(
                select(func.count(User.id)).where(User.bot_id == bot.id)
            ) or 0)
            active_vip = int(await session.scalar(
                select(func.count(Subscription.id)).where(
                    Subscription.bot_id == bot.id,
                    Subscription.access_until.is_not(None),
                    Subscription.access_until > now,
                )
            ) or 0)
            revenue = int(await session.scalar(
                select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)).where(
                    PaymentAttempt.bot_id == bot.id,
                    PaymentAttempt.status.in_(SUCCESS),
                )
            ) or 0)
            delivered = int(await session.scalar(
                select(func.count(DeliveryOutbox.id)).where(
                    DeliveryOutbox.bot_id == bot.id,
                    DeliveryOutbox.status == "delivered",
                )
            ) or 0)
            pending = int(await session.scalar(
                select(func.count(DeliveryOutbox.id)).where(
                    DeliveryOutbox.bot_id == bot.id,
                    DeliveryOutbox.status.in_(("pending", "processing")),
                )
            ) or 0)
            failed = int(await session.scalar(
                select(func.count(DeliveryOutbox.id)).where(
                    DeliveryOutbox.bot_id == bot.id,
                    DeliveryOutbox.status == "failed",
                )
            ) or 0)
            last_delivery = await session.scalar(
                select(func.max(DeliveryOutbox.delivered_at)).where(
                    DeliveryOutbox.bot_id == bot.id
                )
            )
            rows.append(ProjectRow(
                bot=bot,
                users=users,
                active_vip=active_vip,
                revenue_kopecks=revenue,
                delivered=delivered,
                pending=pending,
                failed=failed,
                last_delivery_at=last_delivery,
            ))
        return rows


@router.get("/projects", response_class=HTMLResponse)
async def projects_overview(request: Request):
    if require_session(request) is None:
        return login_redirect(request)
    rows = await project_rows()
    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context=page_context(
            request,
            title="Проекты",
            section="projects",
            rows=rows,
            total_users=sum(row.users for row in rows),
            total_vip=sum(row.active_vip for row in rows),
            total_revenue=sum(row.revenue_kopecks for row in rows),
            total_errors=sum(row.failed for row in rows),
        ),
    )
