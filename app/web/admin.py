from __future__ import annotations

from math import ceil
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.web.admin_auth import AdminAuth, COOKIE_NAME
from app.web.admin_repository import WebAdminRepository
from app.web import admin_ui


settings = load_settings()
auth = AdminAuth(settings)
router = APIRouter(prefix="/admin", include_in_schema=False)
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)

templates.env.filters.update(
    money=admin_ui.money,
    date_time=admin_ui.date_time,
    date_only=admin_ui.date_only,
    status_label=admin_ui.status_label,
    status_tone=admin_ui.status_tone,
    payment_kind=admin_ui.payment_kind,
    delivery_kind=admin_ui.delivery_kind,
    audit_action=admin_ui.audit_action,
    user_name=admin_ui.user_name,
    yes_no=admin_ui.yes_no,
)
templates.env.globals.update(
    status_label=admin_ui.status_label,
    status_tone=admin_ui.status_tone,
    payment_kind=admin_ui.payment_kind,
    delivery_kind=admin_ui.delivery_kind,
    audit_action=admin_ui.audit_action,
    user_name=admin_ui.user_name,
    yes_no=admin_ui.yes_no,
)


money = admin_ui.money


def page_context(
    request: Request,
    *,
    title: str,
    section: str,
    **values,
) -> dict:
    scope = getattr(request.state, "admin_bot_scope", None)
    return {
        "request": request,
        "title": title,
        "section": section,
        "money": money,
        "admin_bots": scope.bots if scope is not None else (),
        "selected_bot": scope.selected if scope is not None else None,
        "selected_bot_id": scope.bot_id if scope is not None else None,
        "selected_bot_code": scope.code if scope is not None else "all",
        "selected_bot_label": scope.label if scope is not None else "Все проекты",
        "current_admin": auth.session_from_request(request),
        **values,
    }


def require_session(request: Request):
    auth.ensure_configured()
    return auth.session_from_request(request)


def login_redirect(request: Request) -> RedirectResponse:
    next_path = request.url.path
    if request.url.query:
        next_path += f"?{request.url.query}"
    return RedirectResponse(
        f"/admin/login?{urlencode({'next': next_path})}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: str = "/admin/business",
):
    auth.ensure_configured()
    if auth.session_from_request(request) is not None:
        return RedirectResponse("/admin/business", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "title": "Вход",
            "next": next if next.startswith("/admin") else "/admin/business",
            "error": None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/admin/business"),
):
    principal = await auth.verify_credentials(username, password)
    if principal is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "title": "Вход",
                "next": next if next.startswith("/admin") else "/admin/business",
                "error": "Неверный логин или пароль",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    destination = next if next.startswith("/admin") else "/admin/business"
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        auth.create_token(principal),
        max_age=settings.web_admin_session_minutes * 60,
        httponly=True,
        secure=settings.web_admin_secure_cookie,
        samesite="strict",
        path="/admin",
    )
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/admin")
    return response


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if require_session(request) is None:
        return login_redirect(request)
    return RedirectResponse(
        "/admin/business",
        status_code=status.HTTP_303_SEE_OTHER,
    )

@router.get("/users", response_class=HTMLResponse)
async def users(
    request: Request,
    q: str = "",
    page: int = 0,
):
    if require_session(request) is None:
        return login_redirect(request)

    page = max(page, 0)
    page_size = 50
    async with SessionFactory() as session:
        rows, total = await WebAdminRepository(session).users(
            query=q,
            page=page,
            page_size=page_size,
        )

    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context=page_context(
            request,
            title="Пользователи",
            section="users",
            rows=rows,
            q=q,
            page=page,
            pages=max(ceil(total / page_size), 1),
            total=total,
        ),
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_details(request: Request, user_id: int):
    if require_session(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        details = await WebAdminRepository(session).user_details(user_id)

    if details is None:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(
        request=request,
        name="user_details.html",
        context=page_context(
            request,
            title=f"Пользователь #{user_id}",
            section="users",
            details=details,
        ),
    )


@router.get("/payments", response_class=HTMLResponse)
async def payments(
    request: Request,
    page: int = 0,
    q: str = "",
    status_filter: str = "",
    kind: str = "",
):
    if require_session(request) is None:
        return login_redirect(request)

    page = max(page, 0)
    page_size = 50
    async with SessionFactory() as session:
        rows, total = await WebAdminRepository(session).payments(
            page=page,
            page_size=page_size,
            query=q,
            status=status_filter,
            kind=kind,
        )

    return templates.TemplateResponse(
        request=request,
        name="payments.html",
        context=page_context(
            request,
            title="Платежи",
            section="payments",
            rows=rows,
            page=page,
            pages=max(ceil(total / page_size), 1),
            total=total,
            q=q,
            status_filter=status_filter,
            kind=kind,
        ),
    )


@router.get("/payments/{attempt_id}", response_class=HTMLResponse)
async def payment_details(request: Request, attempt_id: int):
    if require_session(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        row = await WebAdminRepository(session).payment_details(attempt_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Payment attempt not found")

    attempt, subscription, user, payment_method = row
    return templates.TemplateResponse(
        request=request,
        name="payment_details.html",
        context=page_context(
            request,
            title=f"Платёж #{attempt.id}",
            section="payments",
            attempt=attempt,
            subscription=subscription,
            user=user,
            payment_method=payment_method,
        ),
    )


@router.get("/sources", response_class=HTMLResponse)
async def sources(request: Request):
    if require_session(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        rows = await WebAdminRepository(session).sources()

    return templates.TemplateResponse(
        request=request,
        name="sources.html",
        context=page_context(
            request,
            title="Источники",
            section="sources",
            rows=rows,
        ),
    )


@router.get("/delivery", response_class=HTMLResponse)
async def delivery(request: Request, page: int = 0):
    if require_session(request) is None:
        return login_redirect(request)

    page = max(page, 0)
    page_size = 50
    async with SessionFactory() as session:
        rows, total = await WebAdminRepository(session).delivery(
            page=page,
            page_size=page_size,
        )

    return templates.TemplateResponse(
        request=request,
        name="delivery.html",
        context=page_context(
            request,
            title="Доставка",
            section="delivery",
            rows=rows,
            page=page,
            pages=max(ceil(total / page_size), 1),
            total=total,
        ),
    )


@router.get("/audit", response_class=HTMLResponse)
async def audit(request: Request, page: int = 0):
    if require_session(request) is None:
        return login_redirect(request)

    page = max(page, 0)
    page_size = 50
    async with SessionFactory() as session:
        rows, total = await WebAdminRepository(session).audit(
            page=page,
            page_size=page_size,
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
