from __future__ import annotations

from math import ceil

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from app.database.session import SessionFactory
from app.models.admin import AdminAuditLog
from app.web.admin import login_redirect, page_context, require_session, templates

AUDIT_PATH = "/admin/audit"


async def audit_page(request: Request, page: int = 0):
    principal = require_session(request)
    if principal is None:
        return login_redirect(request)

    scope = getattr(request.state, "admin_bot_scope", None)
    bot_id = getattr(scope, "bot_id", None)
    if bot_id is None and not principal.is_superadmin:
        raise HTTPException(status_code=403, detail="Доступ к общему журналу запрещён")

    page = max(page, 0)
    page_size = 50
    filters = [] if bot_id is None else [AdminAuditLog.bot_id == bot_id]

    async with SessionFactory() as session:
        total = int(
            await session.scalar(
                select(func.count(AdminAuditLog.id)).where(*filters)
            )
            or 0
        )
        rows = list(
            (
                await session.execute(
                    select(AdminAuditLog)
                    .where(*filters)
                    .order_by(AdminAuditLog.id.desc())
                    .offset(page * page_size)
                    .limit(page_size)
                )
            ).scalars()
        )

    return templates.TemplateResponse(
        request=request,
        name="audit.html",
        context=page_context(
            request,
            title="Журнал",
            section="audit",
            rows=rows,
            page=page,
            pages=max(ceil(total / page_size), 1),
            total=total,
        ),
    )


def install_scoped_admin_audit(app) -> None:
    if getattr(app.state, "scoped_admin_audit_installed", False):
        return

    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == AUDIT_PATH
            and "GET" in (getattr(route, "methods", None) or set())
        )
    ]
    app.add_api_route(
        AUDIT_PATH,
        audit_page,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    app.state.scoped_admin_audit_installed = True
