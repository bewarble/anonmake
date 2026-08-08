from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, select

from app.database.session import SessionFactory
from app.models.billing import PaymentAttempt, PaymentMethod
from app.models.marketing import TrafficSource
from app.models.user import User
from app.web.admin import login_redirect, page_context, require_session, templates

router = APIRouter(prefix="/admin", include_in_schema=False)


def _scope_filter(request: Request, model):
    bot_id = getattr(request.state.admin_bot_scope, "bot_id", None)
    if bot_id is None:
        return None
    return model.bot_id == bot_id


@router.get("/search", response_class=HTMLResponse)
async def global_search(request: Request, q: str = ""):
    if require_session(request) is None:
        return login_redirect(request)

    query = q.strip()
    users = []
    payments = []
    methods = []
    sources = []

    if query:
        async with SessionFactory() as session:
            user_filters = [
                User.username.ilike(f"%{query.lstrip('@')}%"),
                User.first_name.ilike(f"%{query}%"),
            ]
            if query.isdigit():
                numeric = int(query)
                user_filters.append(User.telegram_id == numeric)
                if numeric <= 2**31 - 1:
                    user_filters.append(User.id == numeric)
            user_scope = _scope_filter(request, User)
            user_query = select(User).where(or_(*user_filters))
            if user_scope is not None:
                user_query = user_query.where(user_scope)
            users = list(
                (
                    await session.execute(
                        user_query.order_by(User.id.desc()).limit(25)
                    )
                ).scalars()
            )

            payment_filters = [
                PaymentAttempt.customer_operation_id.ilike(f"%{query}%"),
                PaymentAttempt.transaction_id.ilike(f"%{query}%"),
            ]
            if query.isdigit() and int(query) <= 2**31 - 1:
                payment_filters.append(PaymentAttempt.id == int(query))
            payment_scope = _scope_filter(request, PaymentAttempt)
            payment_query = select(PaymentAttempt).where(or_(*payment_filters))
            if payment_scope is not None:
                payment_query = payment_query.where(payment_scope)
            payments = list(
                (
                    await session.execute(
                        payment_query.order_by(PaymentAttempt.id.desc()).limit(25)
                    )
                ).scalars()
            )

            method_scope = _scope_filter(request, PaymentMethod)
            method_query = select(PaymentMethod).where(
                or_(
                    PaymentMethod.binding_id.ilike(f"%{query}%"),
                    PaymentMethod.impaya_user_id.ilike(f"%{query}%"),
                    PaymentMethod.merchant_user_id.ilike(f"%{query}%"),
                )
            )
            if method_scope is not None:
                method_query = method_query.where(method_scope)
            methods = list(
                (
                    await session.execute(
                        method_query.order_by(PaymentMethod.id.desc()).limit(25)
                    )
                ).scalars()
            )

            source_scope = _scope_filter(request, TrafficSource)
            source_query = select(TrafficSource).where(
                or_(
                    TrafficSource.name.ilike(f"%{query}%"),
                    TrafficSource.code.ilike(f"%{query}%"),
                    TrafficSource.source_url.ilike(f"%{query}%"),
                )
            )
            if source_scope is not None:
                source_query = source_query.where(source_scope)
            sources = list(
                (
                    await session.execute(
                        source_query.order_by(TrafficSource.id.desc()).limit(25)
                    )
                ).scalars()
            )

    return templates.TemplateResponse(
        request=request,
        name="global_search.html",
        context=page_context(
            request,
            title="Глобальный поиск",
            section="search",
            q=query,
            users=users,
            payments=payments,
            methods=methods,
            sources=sources,
        ),
    )
