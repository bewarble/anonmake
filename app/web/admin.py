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


settings = load_settings()
auth = AdminAuth(settings)
router = APIRouter(prefix="/admin", include_in_schema=False)
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


def page_context(
    request: Request,
    *,
    title: str,
    section: str,
    **values,
) -> dict:
    return {
        "request": request,
        "title": title,
        "section": section,
        "money": money,
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
    if not auth.verify_credentials(username, password):
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
        auth.create_token(),
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
async def payments(request: Request, page: int = 0):
    if require_session(request) is None:
        return login_redirect(request)

    page = max(page, 0)
    page_size = 50
    async with SessionFactory() as session:
        rows, total = await WebAdminRepository(session).payments(
            page=page,
            page_size=page_size,
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
