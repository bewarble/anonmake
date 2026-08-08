from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.admin import AdminAuditLog
from app.models.billing import PaymentAttempt
from app.models.delivery import DeliveryOutbox
from app.models.platform_admin import AdminProjectAccess, AdminUser, PaymentGatewayConfig
from app.services.redis_client import get_redis
from app.web.admin import login_redirect, page_context, require_session, templates
from app.web.admin_multibot import _allowed_bots, _project_row

PROJECT_DETAILS_PATH = "/admin/projects/{code}"
settings = load_settings()


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
        recent_delivery = list(
            (
                await session.execute(
                    select(DeliveryOutbox)
                    .where(DeliveryOutbox.bot_id == bot.id)
                    .order_by(DeliveryOutbox.created_at.desc())
                    .limit(12)
                )
            ).scalars()
        )
        recent_payments = list(
            (
                await session.execute(
                    select(PaymentAttempt)
                    .where(PaymentAttempt.bot_id == bot.id)
                    .order_by(PaymentAttempt.created_at.desc())
                    .limit(10)
                )
            ).scalars()
        )
        project_admins = list(
            (
                await session.execute(
                    select(AdminUser)
                    .join(
                        AdminProjectAccess,
                        AdminProjectAccess.admin_user_id == AdminUser.id,
                    )
                    .where(AdminProjectAccess.bot_id == bot.id)
                    .order_by(AdminUser.display_name)
                )
            ).scalars()
        )
        recent_audit = list(
            (
                await session.execute(
                    select(AdminAuditLog)
                    .where(AdminAuditLog.bot_id == bot.id)
                    .order_by(AdminAuditLog.created_at.desc())
                    .limit(20)
                )
            ).scalars()
        )

    redis_ok = False
    try:
        redis_ok = bool(
            await asyncio.wait_for(
                get_redis(settings.redis_url).ping(),
                timeout=2.0,
            )
        )
    except Exception:
        redis_ok = False

    last_activity = max(
        (
            value
            for value in (
                row.last_delivery_at,
                row.last_payment_at,
                row.last_user_at,
            )
            if value is not None
        ),
        default=None,
    )

    # A project-owned gateway is authoritative: inactive means payments are
    # intentionally disabled. Global Impaya is only a legacy fallback when no
    # project gateway row exists at all.
    payments_ready = (
        bool(gateway.is_active)
        if gateway is not None
        else bool(settings.impaya_api_token.strip())
    )
    health = {
        "database": True,
        "redis": redis_ok,
        "telegram": row.telegram_ok,
        "delivery": row.failed == 0,
        "payments": payments_ready,
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


def install_scoped_project_details(app) -> None:
    if getattr(app.state, "scoped_project_details_installed", False):
        return

    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == PROJECT_DETAILS_PATH
            and "GET" in (getattr(route, "methods", None) or set())
        )
    ]
    app.add_api_route(
        PROJECT_DETAILS_PATH,
        project_details,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    app.state.scoped_project_details_installed = True
