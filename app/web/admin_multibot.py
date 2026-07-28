from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select

from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.models.billing import PaymentAttempt, Subscription
from app.models.delivery import DeliveryOutbox
from app.models.marketing import Broadcast
from app.models.platform_admin import PaymentGatewayConfig
from app.models.user import User
from app.web.admin import login_redirect, page_context, require_session, templates

router = APIRouter(prefix="/admin", include_in_schema=False)
SUCCESS = ("success", "paid", "completed")


@dataclass(slots=True, frozen=True)
class ProjectRow:
    bot: BotInstance
    users: int
    users_today: int
    active_vip: int
    revenue_today: int
    revenue_week: int
    revenue_month: int
    delivered: int
    pending: int
    failed: int
    active_broadcasts: int
    payment_pending: int
    impaya_ready: bool
    last_delivery_at: datetime | None
    last_error: str | None

    @property
    def operational_status(self) -> str:
        if not self.bot.is_active:
            return "Отключён"
        if self.bot.is_maintenance:
            return "Обслуживание"
        if self.failed:
            return "Есть ошибки"
        if self.pending:
            return "Есть очередь"
        return "Работает"

    @property
    def status_class(self) -> str:
        if not self.bot.is_active:
            return "inactive"
        if self.bot.is_maintenance:
            return "maintenance"
        if self.failed:
            return "warning"
        if self.pending:
            return "pending"
        return "healthy"


async def _count(session, model, *filters) -> int:
    return int(await session.scalar(select(func.count(model.id)).where(*filters)) or 0)


async def _revenue(session, bot_id: int, start: datetime) -> int:
    return int(await session.scalar(
        select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)).where(
            PaymentAttempt.bot_id == bot_id,
            PaymentAttempt.status.in_(SUCCESS),
            PaymentAttempt.created_at >= start,
        )
    ) or 0)


async def _project_row(session, bot: BotInstance, now: datetime) -> ProjectRow:
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = now - timedelta(days=7)
    month = now - timedelta(days=30)
    last_failed = await session.execute(
        select(DeliveryOutbox.last_error)
        .where(
            DeliveryOutbox.bot_id == bot.id,
            DeliveryOutbox.status == "failed",
        )
        .order_by(DeliveryOutbox.updated_at.desc())
        .limit(1)
    )
    gateway = await session.scalar(
        select(PaymentGatewayConfig.id).where(
            PaymentGatewayConfig.bot_id == bot.id,
            PaymentGatewayConfig.provider == "impaya",
            PaymentGatewayConfig.is_active.is_(True),
        )
    )
    return ProjectRow(
        bot=bot,
        users=await _count(session, User, User.bot_id == bot.id),
        users_today=await _count(session, User, User.bot_id == bot.id, User.created_at >= day),
        active_vip=await _count(
            session,
            Subscription,
            Subscription.bot_id == bot.id,
            Subscription.access_until.is_not(None),
            Subscription.access_until > now,
        ),
        revenue_today=await _revenue(session, bot.id, day),
        revenue_week=await _revenue(session, bot.id, week),
        revenue_month=await _revenue(session, bot.id, month),
        delivered=await _count(session, DeliveryOutbox, DeliveryOutbox.bot_id == bot.id, DeliveryOutbox.status == "delivered"),
        pending=await _count(session, DeliveryOutbox, DeliveryOutbox.bot_id == bot.id, DeliveryOutbox.status.in_(("pending", "processing"))),
        failed=await _count(session, DeliveryOutbox, DeliveryOutbox.bot_id == bot.id, DeliveryOutbox.status == "failed"),
        active_broadcasts=await _count(session, Broadcast, Broadcast.bot_id == bot.id, Broadcast.status.in_(("draft", "scheduled", "processing"))),
        payment_pending=await _count(session, PaymentAttempt, PaymentAttempt.bot_id == bot.id, PaymentAttempt.status == "pending"),
        impaya_ready=gateway is not None,
        last_delivery_at=await session.scalar(select(func.max(DeliveryOutbox.delivered_at)).where(DeliveryOutbox.bot_id == bot.id)),
        last_error=last_failed.scalar_one_or_none(),
    )


async def _allowed_bots(request: Request) -> tuple[BotInstance, ...]:
    scope = getattr(request.state, "admin_bot_scope", None)
    return tuple(scope.bots) if scope is not None else ()


@router.get("/projects", response_class=HTMLResponse)
async def projects_overview(request: Request):
    if require_session(request) is None:
        return login_redirect(request)
    now = datetime.now(timezone.utc)
    allowed = await _allowed_bots(request)
    async with SessionFactory() as session:
        rows = [await _project_row(session, bot, now) for bot in allowed]
    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context=page_context(
            request,
            title="Центр управления проектами",
            section="projects",
            rows=rows,
            total_users=sum(row.users for row in rows),
            total_vip=sum(row.active_vip for row in rows),
            total_revenue=sum(row.revenue_month for row in rows),
            total_errors=sum(row.failed for row in rows),
        ),
    )


@router.get("/projects/{code}", response_class=HTMLResponse)
async def project_details(request: Request, code: str):
    if require_session(request) is None:
        return login_redirect(request)
    allowed = await _allowed_bots(request)
    bot = next((item for item in allowed if item.code == code), None)
    if bot is None:
        raise HTTPException(status_code=403, detail="Доступ к проекту запрещён")
    async with SessionFactory() as session:
        row = await _project_row(session, bot, datetime.now(timezone.utc))
        recent_delivery = list((await session.execute(
            select(DeliveryOutbox)
            .where(DeliveryOutbox.bot_id == bot.id)
            .order_by(DeliveryOutbox.created_at.desc())
            .limit(12)
        )).scalars())
        recent_payments = list((await session.execute(
            select(PaymentAttempt)
            .where(PaymentAttempt.bot_id == bot.id)
            .order_by(PaymentAttempt.created_at.desc())
            .limit(10)
        )).scalars())
    return templates.TemplateResponse(
        request=request,
        name="project_details.html",
        context=page_context(
            request,
            title=bot.display_name,
            section="projects",
            row=row,
            recent_delivery=recent_delivery,
            recent_payments=recent_payments,
            notice=request.query_params.get("notice"),
        ),
    )


@router.post("/projects/{code}/settings")
async def update_project(
    request: Request,
    code: str,
    display_name: str = Form(...),
    is_active: bool = Form(False),
    is_maintenance: bool = Form(False),
    maintenance_message: str = Form(""),
):
    principal = require_session(request)
    if principal is None:
        return login_redirect(request)
    if not principal.is_superadmin:
        raise HTTPException(status_code=403, detail="Настройки проекта доступны только суперадминистратору")
    async with SessionFactory() as session:
        bot = await session.scalar(select(BotInstance).where(BotInstance.code == code))
        if bot is None:
            raise HTTPException(status_code=404, detail="Проект не найден")
        bot.display_name = display_name.strip()[:96]
        bot.is_active = is_active
        bot.is_maintenance = is_maintenance
        bot.maintenance_message = maintenance_message.strip() or None
        await session.commit()
    return RedirectResponse(f"/admin/projects/{code}?notice=saved", status_code=303)
