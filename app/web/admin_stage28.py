from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.database.session import SessionFactory
from app.web.admin import login_redirect, page_context, require_session, templates
from app.web.admin_repository import WebAdminRepository
from app.web.admin_repository_stage27 import WebCrmRepository
from app.web.admin_repository_stage28 import WebAdminProRepository

router = APIRouter(prefix="/admin", include_in_schema=False)


def serialize_periods(rows):
    return [
        {
            "label": row.label,
            "users": row.users,
            "questions": row.questions,
            "answers": row.answers,
            "revenue": round(row.revenue_kopecks / 100, 2),
        }
        for row in rows
    ]


@router.get("/pro", response_class=HTMLResponse)
async def pro_dashboard(request: Request):
    if require_session(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        base = await WebAdminRepository(session).dashboard()
        crm = WebCrmRepository(session)
        pro = WebAdminProRepository(session)

        periods = await pro.periods(14)
        funnel = await pro.funnel()
        sources = await pro.source_performance()
        operations = await pro.operations()
        thirty_day_chart = await crm.chart(30)

    return templates.TemplateResponse(
        request=request,
        name="pro_dashboard.html",
        context=page_context(
            request,
            title="Growth Overview",
            section="dashboard",
            base=base,
            periods=periods,
            periods_json=serialize_periods(periods),
            funnel=funnel,
            sources=sources,
            operations=operations,
            thirty_day_chart=thirty_day_chart,
        ),
    )


@router.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request):
    if require_session(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        pro = WebAdminProRepository(session)
        periods = await pro.periods(30)
        funnel = await pro.funnel()
        sources = await pro.source_performance(limit=20)

    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context=page_context(
            request,
            title="Аналитика",
            section="analytics",
            periods=periods,
            periods_json=serialize_periods(periods),
            funnel=funnel,
            sources=sources,
        ),
    )


@router.get("/api/analytics/periods")
async def analytics_periods(request: Request, days: int = 30):
    if require_session(request) is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)

    days = min(max(days, 7), 90)
    async with SessionFactory() as session:
        rows = await WebAdminProRepository(session).periods(days)

    return {"items": serialize_periods(rows)}
