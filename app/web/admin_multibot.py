from __future__ import annotations

from dataclasses import dataclass
import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from app.core.config import load_settings
from app.core.platform_security import encrypt_secret
from app.database.session import SessionFactory
from app.models.admin import AdminAuditLog
from app.models.bot_instance import BotInstance
from app.models.billing import PaymentAttempt, Subscription
from app.models.delivery import DeliveryOutbox
from app.models.marketing import Broadcast
from app.models.platform_admin import AdminProjectAccess, AdminUser, PaymentGatewayConfig
from app.models.project_setup import ProjectSetupDraft
from app.models.question import Question
from app.models.user import User
from app.services.bot_credentials import resolve_bot_token, token_hint, verify_telegram_token
from app.services.redis_client import get_redis
from app.web.admin import login_redirect, page_context, require_session, templates

router = APIRouter(prefix="/admin", include_in_schema=False)
SUCCESS = ("success", "paid", "completed")
settings = load_settings()


@dataclass(slots=True, frozen=True)
class ProjectRow:
    bot: BotInstance
    users: int
    users_today: int
    messages: int
    messages_today: int
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
    last_payment_at: datetime | None
    last_user_at: datetime | None
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


async def _question_count(session, bot_id: int, start: datetime | None = None) -> int:
    recipient = aliased(User)
    statement = (
        select(func.count(Question.id))
        .join(recipient, recipient.id == Question.recipient_id)
        .where(recipient.bot_id == bot_id)
    )
    if start is not None:
        statement = statement.where(Question.created_at >= start)
    return int(await session.scalar(statement) or 0)


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
        messages=await _question_count(session, bot.id),
        messages_today=await _question_count(session, bot.id, day),
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
        last_payment_at=await session.scalar(select(func.max(PaymentAttempt.created_at)).where(PaymentAttempt.bot_id == bot.id)),
        last_user_at=await session.scalar(select(func.max(User.created_at)).where(User.bot_id == bot.id)),
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
        drafts = list((await session.execute(select(ProjectSetupDraft).where(ProjectSetupDraft.status.in_(("draft", "needs_attention", "ready"))).order_by(ProjectSetupDraft.updated_at.desc()))).scalars()) if require_session(request).is_superadmin else []
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
            drafts=drafts,
        ),
    )


@router.get("/projects/{code}", response_class=HTMLResponse)
async def project_details(request: Request, code: str, tab: str = "overview"):
    principal = require_session(request)
    if principal is None:
        return login_redirect(request)
    allowed = await _allowed_bots(request)
    bot = next((item for item in allowed if item.code == code), None)
    if bot is None:
        raise HTTPException(status_code=403, detail="Доступ к проекту запрещён")

    allowed_tabs = {"overview", "telegram", "payments", "admins", "activity", "settings"}
    active_tab = tab if tab in allowed_tabs else "overview"
    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        row = await _project_row(session, bot, now)
        gateway = await session.scalar(
            select(PaymentGatewayConfig).where(
                PaymentGatewayConfig.bot_id == bot.id,
                PaymentGatewayConfig.provider == "impaya",
            )
        )
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
        project_admins = list((await session.execute(
            select(AdminUser)
            .join(AdminProjectAccess, AdminProjectAccess.admin_user_id == AdminUser.id)
            .where(AdminProjectAccess.bot_id == bot.id)
            .order_by(AdminUser.display_name)
        )).scalars())
        recent_audit = list((await session.execute(
            select(AdminAuditLog)
            .where(or_(
                AdminAuditLog.target == bot.code,
                AdminAuditLog.target == str(bot.id),
                AdminAuditLog.details.ilike(f"%{bot.code}%"),
            ))
            .order_by(AdminAuditLog.created_at.desc())
            .limit(20)
        )).scalars())

    redis_ok = False
    try:
        redis_ok = bool(await asyncio.wait_for(get_redis(settings.redis_url).ping(), timeout=2.0))
    except Exception:
        redis_ok = False

    last_activity = max(
        (value for value in (row.last_delivery_at, row.last_payment_at, row.last_user_at) if value is not None),
        default=None,
    )
    health = {
        "database": True,
        "redis": redis_ok,
        "telegram": bool(bot.is_active and (bot.token_verified_at or bot.runtime_mode == "external")),
        "delivery": row.failed == 0,
        "payments": row.impaya_ready or bool(settings.impaya_api_token),
    }
    return templates.TemplateResponse(
        request=request,
        name="project_details.html",
        context=page_context(
            request,
            title=bot.display_name,
            section="projects",
            row=row,
            gateway=gateway,
            project_admins=project_admins,
            recent_audit=recent_audit,
            recent_delivery=recent_delivery,
            recent_payments=recent_payments,
            active_tab=active_tab,
            health=health,
            last_activity=last_activity,
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


@router.get("/projects/create/new", response_class=HTMLResponse)
async def project_create_page(request: Request):
    principal = require_session(request)
    if principal is None:
        return login_redirect(request)
    if not principal.is_superadmin:
        raise HTTPException(status_code=403, detail="Создание проекта доступно только суперадминистратору")
    return RedirectResponse("/admin/projects/create/wizard", status_code=303)


@router.post("/projects/create/new")
async def create_project(
    request: Request,
    code: str = Form(...),
    display_name: str = Form(...),
    telegram_token: str = Form(...),
):
    principal = require_session(request)
    if principal is None:
        return login_redirect(request)
    if not principal.is_superadmin:
        raise HTTPException(status_code=403, detail="Создание проекта доступно только суперадминистратору")
    normalized = code.strip().lower().replace("-", "_")
    if not normalized or not normalized.replace("_", "").isalnum() or len(normalized) > 32:
        return RedirectResponse("/admin/projects/create/new?error=code", status_code=303)
    token = telegram_token.strip()
    try:
        me = await verify_telegram_token(token)
    except Exception:
        return RedirectResponse("/admin/projects/create/new?error=token", status_code=303)
    async with SessionFactory() as session:
        exists = await session.scalar(select(BotInstance.id).where((BotInstance.code == normalized) | (BotInstance.username == me.username)))
        if exists:
            return RedirectResponse("/admin/projects/create/new?error=exists", status_code=303)
        item = BotInstance(
            code=normalized,
            username=me.username,
            display_name=display_name.strip()[:96],
            runtime_mode="managed",
            telegram_bot_id=me.id,
            token_encrypted=encrypt_secret(token, settings.web_admin_secret),
            token_hint=token_hint(token),
            token_verified_at=datetime.now(timezone.utc),
            is_active=True,
        )
        session.add(item)
        await session.commit()
    return RedirectResponse(f"/admin/projects/{normalized}?notice=created", status_code=303)


@router.post("/projects/{code}/telegram/check")
async def check_project_telegram(request: Request, code: str):
    principal = require_session(request)
    if principal is None:
        return login_redirect(request)
    allowed = await _allowed_bots(request)
    item = next((bot for bot in allowed if bot.code == code), None)
    if item is None:
        raise HTTPException(status_code=403, detail="Доступ к проекту запрещён")
    try:
        async with SessionFactory() as session:
            item = await session.scalar(select(BotInstance).where(BotInstance.code == code))
            if item is None:
                raise HTTPException(status_code=404, detail="Проект не найден")
            token = await resolve_bot_token(session, settings, item)
            me = await verify_telegram_token(token)
            item.username = me.username
            item.telegram_bot_id = me.id
            item.token_verified_at = datetime.now(timezone.utc)
            await session.commit()
    except HTTPException:
        raise
    except Exception:
        return RedirectResponse(f"/admin/projects/{code}?tab=telegram&notice=token_error", status_code=303)
    return RedirectResponse(f"/admin/projects/{code}?tab=telegram&notice=telegram_ok", status_code=303)


@router.post("/projects/{code}/telegram")
async def update_project_token(request: Request, code: str, telegram_token: str = Form(...)):
    principal = require_session(request)
    if principal is None:
        return login_redirect(request)
    if not principal.is_superadmin:
        raise HTTPException(status_code=403, detail="Настройки Telegram доступны только суперадминистратору")
    token = telegram_token.strip()
    try:
        me = await verify_telegram_token(token)
    except Exception:
        return RedirectResponse(f"/admin/projects/{code}?tab=telegram&notice=token_error", status_code=303)
    async with SessionFactory() as session:
        item = await session.scalar(select(BotInstance).where(BotInstance.code == code))
        if item is None:
            raise HTTPException(status_code=404, detail="Проект не найден")
        item.username = me.username
        item.telegram_bot_id = me.id
        item.token_encrypted = encrypt_secret(token, settings.web_admin_secret)
        item.token_hint = token_hint(token)
        item.token_verified_at = datetime.now(timezone.utc)
        item.runtime_mode = "managed"
        await session.commit()
    return RedirectResponse(f"/admin/projects/{code}?tab=telegram&notice=token_saved", status_code=303)
