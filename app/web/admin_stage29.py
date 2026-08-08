from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
import logging
from math import ceil

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.bot_context import CurrentBot, reset_current_bot, set_current_bot
from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.billing import Subscription
from app.models.bot_instance import BotInstance
from app.models.marketing import TrafficSource
from app.repositories.marketing import MarketingRepository
from app.web.admin import login_redirect, page_context, require_session, templates
from app.web.admin_auth import COOKIE_NAME
from app.web.admin_repository_stage29 import Stage29Repository

router = APIRouter(prefix="/admin", include_in_schema=False)
settings = load_settings()
logger = logging.getLogger(__name__)


def csrf_token(request: Request, action: str) -> str:
    session_token = request.cookies.get(COOKIE_NAME, "")
    if not session_token:
        return ""
    return hmac.new(
        settings.web_admin_secret.encode("utf-8"),
        (action + ":" + session_token).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_csrf(request: Request, action: str, received: str) -> None:
    expected = csrf_token(request, action)
    if not expected or not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def parse_period(value: str) -> int | None:
    if value == "all":
        return None
    try:
        return min(max(int(value), 1), 365)
    except ValueError:
        return 1


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
        CurrentBot(
            instance.id,
            instance.code,
            instance.username,
            instance.display_name,
        )
    )
    try:
        yield
    finally:
        reset_current_bot(token)


async def _scoped_source(
    session,
    request: Request,
    source_id: int,
) -> TrafficSource | None:
    statement = select(TrafficSource).where(TrafficSource.id == source_id)
    bot_id = _scope_bot_id(request)
    if bot_id is not None:
        statement = statement.where(TrafficSource.bot_id == bot_id)
    return await session.scalar(statement)


def source_referral_url(source: TrafficSource, bot_username: str) -> str:
    username = bot_username.strip().lstrip("@")
    payload = f"src_{source.code}"
    if not username:
        return payload
    return f"https://t.me/{username}?start={payload}"


@router.get("/business", response_class=HTMLResponse)
async def business_dashboard(request: Request, period: str = "1"):
    if require_session(request) is None:
        return login_redirect(request)

    days = parse_period(period)
    chart_days = 7 if days in (None, 1) else min(max(days, 7), 90)

    async with SessionFactory() as session:
        repository = Stage29Repository(session, bot_id=_scope_bot_id(request))
        snapshot = await repository.dashboard(days)
        chart = await repository.chart(chart_days)
        sources = await repository.sources()

    chart_json = [
        {
            "label": item.label,
            "users": item.users,
            "blocked": item.blocked,
            "questions": item.questions,
            "answers": item.answers,
            "revenue": round(item.revenue_kopecks / 100, 2),
        }
        for item in chart
    ]

    return templates.TemplateResponse(
        request=request,
        name="business_dashboard.html",
        context=page_context(
            request,
            title="Бизнес-обзор",
            section="dashboard",
            snapshot=snapshot,
            chart_json=chart_json,
            period=period,
            chart_days=chart_days,
            sources=sources[:6],
        ),
    )


@router.get("/business/users", response_class=HTMLResponse)
async def business_users(
    request: Request,
    q: str = "",
    vip: str = "all",
    health: str = "all",
    source_id: str = "",
    page: int = 0,
):
    if require_session(request) is None:
        return login_redirect(request)

    parsed_source = int(source_id) if source_id.isdigit() else None
    page = max(page, 0)
    page_size = 50

    async with SessionFactory() as session:
        repository = Stage29Repository(session, bot_id=_scope_bot_id(request))
        rows, total = await repository.users(
            query=q,
            vip=vip,
            health=health,
            source_id=parsed_source,
            page=page,
            page_size=page_size,
        )
        sources = await repository.sources()

    return templates.TemplateResponse(
        request=request,
        name="business_users.html",
        context=page_context(
            request,
            title="Пользователи",
            section="users",
            rows=rows,
            total=total,
            sources=sources,
            q=q,
            vip=vip,
            health=health,
            source_id=parsed_source,
            page=page,
            pages=max(ceil(total / page_size), 1),
        ),
    )


@router.get("/business/sources", response_class=HTMLResponse)
async def business_sources(request: Request):
    if require_session(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        rows = await Stage29Repository(
            session,
            bot_id=_scope_bot_id(request),
        ).sources()

    return templates.TemplateResponse(
        request=request,
        name="business_sources.html",
        context=page_context(
            request,
            title="Источники",
            section="sources",
            rows=rows,
        ),
    )


@router.get("/business/sources/new", response_class=HTMLResponse)
async def source_new_page(request: Request):
    if require_session(request) is None:
        return login_redirect(request)
    _selected_bot(request)

    return templates.TemplateResponse(
        request=request,
        name="business_source_form.html",
        context=page_context(
            request,
            title="Новый источник",
            section="sources",
            csrf=csrf_token(request, "source-create"),
            action="/admin/business/sources/new",
            error=None,
            values={},
        ),
    )


@router.post("/business/sources/new")
async def source_new_submit(
    request: Request,
    name: str = Form(...),
    source_url: str = Form(...),
    spend_rubles: str = Form(...),
    csrf: str = Form(...),
):
    if require_session(request) is None:
        return login_redirect(request)
    verify_csrf(request, "source-create", csrf)
    selected_bot = _selected_bot(request)

    name = name.strip()
    source_url = source_url.strip()
    try:
        spend_kopecks = round(float(spend_rubles.replace(",", ".") or "0") * 100)
    except ValueError:
        spend_kopecks = -1

    error = None
    if not name:
        error = "Укажите название."
    elif not source_url.startswith(("http://", "https://")):
        error = "Укажите корректную ссылку."
    elif spend_kopecks < 0:
        error = "Укажите корректную сумму."

    if error:
        return templates.TemplateResponse(
            request=request,
            name="business_source_form.html",
            context=page_context(
                request,
                title="Новый источник",
                section="sources",
                csrf=csrf_token(request, "source-create"),
                action="/admin/business/sources/new",
                error=error,
                values={
                    "name": name,
                    "source_url": source_url,
                    "spend_rubles": spend_rubles,
                },
            ),
            status_code=422,
        )

    async with SessionFactory() as session:
        with _bot_context(selected_bot):
            source = await MarketingRepository(session).create_source(
                name=name,
                source_url=source_url,
                spend_kopecks=spend_kopecks,
                admin_telegram_id=next(iter(settings.admin_ids_set), 0),
            )
        await session.commit()
        source_id = source.id

    return RedirectResponse(
        f"/admin/business/sources/{source_id}",
        status_code=303,
    )


@router.get("/business/sources/{source_id}", response_class=HTMLResponse)
async def source_details(request: Request, source_id: int):
    if require_session(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        source = await _scoped_source(session, request, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")
        owner = await session.get(BotInstance, source.bot_id)
        rows = await Stage29Repository(
            session,
            bot_id=_scope_bot_id(request),
        ).sources()

    if owner is None:
        raise HTTPException(status_code=404, detail="Source project not found")

    row = next((item for item in rows if item.source.id == source_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return templates.TemplateResponse(
        request=request,
        name="business_source_details.html",
        context=page_context(
            request,
            title=source.name,
            section="sources",
            row=row,
            referral_url=source_referral_url(source, owner.username),
            csrf_edit=csrf_token(request, f"source-edit-{source_id}"),
            csrf_delete=csrf_token(request, f"source-delete-{source_id}"),
        ),
    )


@router.post("/business/sources/{source_id}/edit")
async def source_edit(
    request: Request,
    source_id: int,
    name: str = Form(...),
    source_url: str = Form(...),
    spend_rubles: str = Form(...),
    is_active: str = Form(""),
    csrf: str = Form(...),
):
    if require_session(request) is None:
        return login_redirect(request)
    verify_csrf(request, f"source-edit-{source_id}", csrf)

    try:
        spend_kopecks = round(float(spend_rubles.replace(",", ".") or "0") * 100)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid spend") from exc

    async with SessionFactory() as session:
        source = await _scoped_source(session, request, source_id)
        if source is None:
            raise HTTPException(status_code=404)
        source.name = name.strip()
        source.source_url = source_url.strip()
        source.spend_kopecks = max(spend_kopecks, 0)
        source.is_active = is_active == "on"
        await session.commit()

    return RedirectResponse(
        f"/admin/business/sources/{source_id}",
        status_code=303,
    )


@router.post("/business/sources/{source_id}/delete")
async def source_delete(
    request: Request,
    source_id: int,
    csrf: str = Form(...),
):
    if require_session(request) is None:
        return login_redirect(request)
    verify_csrf(request, f"source-delete-{source_id}", csrf)

    async with SessionFactory() as session:
        source = await _scoped_source(session, request, source_id)
        if source is not None:
            await session.delete(source)
            await session.commit()

    return RedirectResponse("/admin/business/sources", status_code=303)


@router.get("/business/broadcasts", response_class=HTMLResponse)
async def broadcasts_page(request: Request, created: int = 0):
    if require_session(request) is None:
        return login_redirect(request)
    selected_bot = _selected_bot(request)

    async with SessionFactory() as session:
        with _bot_context(selected_bot):
            marketing = MarketingRepository(session)
            rows = await marketing.recent_broadcasts(limit=50)
            broadcast_stats = {
                row.id: await marketing.broadcast_delivery_stats(row.id)
                for row in rows
            }
            audience_counts = {
                key: await marketing.broadcast_audience_count(key)
                for key in ("all", "vip", "non_vip")
            }

    return templates.TemplateResponse(
        request=request,
        name="business_broadcasts.html",
        context=page_context(
            request,
            title="Рассылки",
            section="broadcasts",
            rows=rows,
            broadcast_stats=broadcast_stats,
            audience_counts=audience_counts,
            csrf=csrf_token(request, "broadcast-create"),
            error=None,
            created=bool(created),
        ),
    )


@router.post("/business/broadcasts", response_class=HTMLResponse)
async def broadcast_create(
    request: Request,
    audience: str = Form(...),
    text: str = Form(...),
    csrf: str = Form(...),
):
    if require_session(request) is None:
        return login_redirect(request)
    verify_csrf(request, "broadcast-create", csrf)
    selected_bot = _selected_bot(request)

    audience = audience if audience in {"all", "vip", "non_vip"} else "all"
    text = text.strip()

    if not text:
        error = "Введите текст рассылки."
    elif len(text) > 1500:
        error = "Текст не должен превышать 1500 символов."
    else:
        error = None

    if error is None:
        try:
            async with SessionFactory() as session:
                with _bot_context(selected_bot):
                    await MarketingRepository(session).create_broadcast(
                        kind="anonymous",
                        audience=audience,
                        text=text,
                        admin_telegram_id=next(iter(settings.admin_ids_set), 0),
                    )
                await session.commit()
            return RedirectResponse(
                "/admin/business/broadcasts?created=1",
                status_code=303,
            )
        except SQLAlchemyError:
            logger.exception("Could not create web broadcast")
            error = "Не удалось создать рассылку. Ошибка записана в журнал web."

    async with SessionFactory() as session:
        with _bot_context(selected_bot):
            marketing = MarketingRepository(session)
            rows = await marketing.recent_broadcasts(limit=50)
            broadcast_stats = {
                row.id: await marketing.broadcast_delivery_stats(row.id)
                for row in rows
            }
            audience_counts = {
                key: await marketing.broadcast_audience_count(key)
                for key in ("all", "vip", "non_vip")
            }

    return templates.TemplateResponse(
        request=request,
        name="business_broadcasts.html",
        context=page_context(
            request,
            title="Рассылки",
            section="broadcasts",
            rows=rows,
            broadcast_stats=broadcast_stats,
            audience_counts=audience_counts,
            csrf=csrf_token(request, "broadcast-create"),
            error=error,
            created=False,
            values={"audience": audience, "text": text},
        ),
        status_code=422,
    )


@router.get("/business/api/chart")
async def chart_api(request: Request, days: int = 30):
    if require_session(request) is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)

    days = min(max(days, 7), 90)
    async with SessionFactory() as session:
        rows = await Stage29Repository(
            session,
            bot_id=_scope_bot_id(request),
        ).chart(days)

    return {
        "items": [
            {
                "label": item.label,
                "users": item.users,
                "blocked": item.blocked,
                "questions": item.questions,
                "answers": item.answers,
                "revenue": round(item.revenue_kopecks / 100, 2),
            }
            for item in rows
        ]
    }
