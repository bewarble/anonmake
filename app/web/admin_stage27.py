from __future__ import annotations

from math import ceil

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.database.session import SessionFactory
from app.web.admin import login_redirect, page_context, require_session, templates
from app.web.admin_repository import WebAdminRepository
from app.web.admin_repository_stage27 import WebCrmRepository

router = APIRouter(prefix="/admin", include_in_schema=False)


def parse_optional_positive_int(value: str | None) -> int | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    try:
        parsed = int(cleaned)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_v2(request: Request):
    if require_session(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        data = await WebAdminRepository(session).dashboard()
        chart = await WebCrmRepository(session).chart(30)
    return templates.TemplateResponse(
        request=request,
        name="dashboard_v2.html",
        context=page_context(
            request,
            title="Обзор",
            section="dashboard",
            data=data,
            chart=chart,
        ),
    )


@router.get("/crm/users", response_class=HTMLResponse)
async def crm_users(
    request: Request,
    q: str = "",
    vip: str = "all",
    health: str = "all",
    page: int = 0,
):
    if require_session(request) is None:
        return login_redirect(request)

    vip = vip if vip in {"all", "active", "inactive"} else "all"
    health = health if health in {"all", "alive", "dead"} else "all"
    source_id = parse_optional_positive_int(
        request.query_params.get("source_id")
    )

    page = max(page, 0)
    page_size = 50

    async with SessionFactory() as session:
        repository = WebCrmRepository(session)
        rows, total = await repository.users(
            query=q,
            vip=vip,
            health=health,
            source_id=source_id,
            page=page,
            page_size=page_size,
        )
        sources = await repository.sources()

    return templates.TemplateResponse(
        request=request,
        name="crm_users.html",
        context=page_context(
            request,
            title="Пользователи",
            section="users",
            rows=rows,
            sources=sources,
            q=q,
            vip=vip,
            health=health,
            source_id=source_id,
            page=page,
            pages=max(ceil(total / page_size), 1),
            total=total,
        ),
    )


@router.get("/crm/users/{user_id}", response_class=HTMLResponse)
async def crm_user_details(request: Request, user_id: int):
    if require_session(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        details = await WebAdminRepository(session).user_details(user_id)
        timeline = await WebCrmRepository(session).user_timeline(user_id)
    if details is None:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse(
        request=request,
        name="crm_user_details.html",
        context=page_context(
            request,
            title=f"Пользователь #{user_id}",
            section="users",
            details=details,
            timeline=timeline,
        ),
    )


@router.get("/crm/sources/{source_id}", response_class=HTMLResponse)
async def crm_source_details(request: Request, source_id: int):
    if require_session(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        details = await WebCrmRepository(session).source_details(source_id)
    if details is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return templates.TemplateResponse(
        request=request,
        name="crm_source_details.html",
        context=page_context(
            request,
            title=details.source.name,
            section="sources",
            details=details,
        ),
    )


@router.get("/broadcasts", response_class=HTMLResponse)
async def broadcasts(request: Request, page: int = 0):
    if require_session(request) is None:
        return login_redirect(request)
    page = max(page, 0)
    page_size = 50
    async with SessionFactory() as session:
        rows, total = await WebCrmRepository(session).broadcasts(page, page_size)
    return templates.TemplateResponse(
        request=request,
        name="broadcasts.html",
        context=page_context(
            request,
            title="Рассылки",
            section="broadcasts",
            rows=rows,
            page=page,
            pages=max(ceil(total / page_size), 1),
            total=total,
        ),
    )
