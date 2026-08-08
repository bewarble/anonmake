from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.database.session import SessionFactory
from app.web.admin import login_redirect, page_context, require_session, templates
from app.web.admin_repository_stage29 import Stage29Repository

router = APIRouter(prefix="/admin", include_in_schema=False)


def parse_period(value: str) -> int | None:
    if value == "all":
        return None
    try:
        return min(max(int(value), 1), 90)
    except ValueError:
        return 30


def _scope_bot_id(request: Request) -> int | None:
    scope = getattr(request.state, "admin_bot_scope", None)
    return getattr(scope, "bot_id", None)


@router.get("/business/analytics", response_class=HTMLResponse)
async def business_analytics(request: Request, period: str = "1"):
    if require_session(request) is None:
        return login_redirect(request)

    days = parse_period(period)
    chart_days = 90 if days is None else (7 if days == 1 else days)

    async with SessionFactory() as session:
        repository = Stage29Repository(session, bot_id=_scope_bot_id(request))
        chart = await repository.chart(chart_days)
        snapshot = await repository.dashboard(days)

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
        name="business_analytics.html",
        context=page_context(
            request,
            title="Аналитика",
            section="analytics",
            period=period,
            chart_days=chart_days,
            snapshot=snapshot,
            chart_json=chart_json,
        ),
    )
