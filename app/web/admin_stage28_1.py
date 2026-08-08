from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.bot_context import CurrentBot, reset_current_bot, set_current_bot
from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.repositories.marketing import MarketingRepository
from app.web.admin import login_redirect, page_context, require_session, templates
from app.web.admin_auth import COOKIE_NAME
from app.web.admin_repository_stage27 import WebCrmRepository
from app.web.admin_repository_stage28 import WebAdminProRepository
from app.web.admin_scoped_repository import ScopedWebAdminRepository

router = APIRouter(prefix="/admin", include_in_schema=False)
settings = load_settings()


def csrf_token(request: Request) -> str:
    session_token = request.cookies.get(COOKIE_NAME, "")
    if not session_token:
        return ""
    return hmac.new(
        settings.web_admin_secret.encode("utf-8"),
        ("source-create:" + session_token).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_csrf(request: Request, received: str) -> None:
    expected = csrf_token(request)
    if not expected or not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def _scope_bot_id(request: Request) -> int | None:
    return getattr(request.state.admin_bot_scope, "bot_id", None)


def _selected_bot(request: Request) -> BotInstance:
    selected = getattr(request.state.admin_bot_scope, "selected", None)
    if selected is None:
        raise HTTPException(
            status_code=400,
            detail="Выберите проект для выполнения этого действия",
        )
    return selected


@contextmanager
def _bot_context(instance: BotInstance):
    token = set_current_bot(
        CurrentBot(instance.id, instance.code, instance.username, instance.display_name)
    )
    try:
        yield
    finally:
        reset_current_bot(token)


@router.get("/overview", response_class=HTMLResponse)
async def overview(request: Request):
    if require_session(request) is None:
        return login_redirect(request)

    bot_id = _scope_bot_id(request)
    async with SessionFactory() as session:
        base = await ScopedWebAdminRepository(session, bot_id=bot_id).dashboard()
        pro = WebAdminProRepository(session, bot_id=bot_id)
        periods = await pro.periods(14)
        funnel = await pro.funnel()
        sources = await pro.source_performance()
        operations = await pro.operations()

    periods_json = [
        {
            "label": row.label,
            "users": row.users,
            "questions": row.questions,
            "answers": row.answers,
            "revenue": round(row.revenue_kopecks / 100, 2),
        }
        for row in periods
    ]

    return templates.TemplateResponse(
        request=request,
        name="pro_dashboard_28_1.html",
        context=page_context(
            request,
            title="Обзор",
            section="dashboard",
            base=base,
            periods_json=periods_json,
            funnel=funnel,
            sources=sources,
            operations=operations,
        ),
    )


@router.get("/sources/new", response_class=HTMLResponse)
async def source_create_page(request: Request):
    if require_session(request) is None:
        return login_redirect(request)
    _selected_bot(request)

    return templates.TemplateResponse(
        request=request,
        name="source_create.html",
        context=page_context(
            request,
            title="Новый источник",
            section="sources",
            csrf_token=csrf_token(request),
            values={},
            error=None,
        ),
    )


@router.post("/sources/new", response_class=HTMLResponse)
async def source_create_submit(
    request: Request,
    name: str = Form(...),
    source_url: str = Form(...),
    spend_rubles: str = Form(...),
    csrf: str = Form(...),
):
    session_data = require_session(request)
    if session_data is None:
        return login_redirect(request)

    verify_csrf(request, csrf)
    selected_bot = _selected_bot(request)

    name = name.strip()
    source_url = source_url.strip()
    spend_raw = spend_rubles.strip().replace(" ", "").replace(",", ".")
    error = None

    if not name:
        error = "Укажите название источника."
    elif not source_url.startswith(("http://", "https://")):
        error = "Ссылка должна начинаться с http:// или https://."

    spend_kopecks = 0
    if error is None:
        try:
            amount = float(spend_raw or "0")
            if amount < 0:
                raise ValueError
            spend_kopecks = round(amount * 100)
        except ValueError:
            error = "Укажите корректную сумму закупа."

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="source_create.html",
            context=page_context(
                request,
                title="Новый источник",
                section="sources",
                csrf_token=csrf_token(request),
                values={
                    "name": name,
                    "source_url": source_url,
                    "spend_rubles": spend_rubles,
                },
                error=error,
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    async with SessionFactory() as session:
        with _bot_context(selected_bot):
            source = await MarketingRepository(session).create_source(
                name=name,
                source_url=source_url,
                spend_kopecks=spend_kopecks,
                admin_telegram_id=0,
            )
        await session.commit()
        source_id = source.id

    return RedirectResponse(
        "/admin/crm/sources/" + str(source_id) + "?created=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )
