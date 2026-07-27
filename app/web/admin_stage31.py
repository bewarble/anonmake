from __future__ import annotations

from datetime import timedelta
from math import ceil
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, or_, select

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models import User
from app.models.billing import PaymentMethod, Subscription
from app.services.admin_subscription_control import AdminSubscriptionControl
from app.services.impaya import ImpayaClient
from app.web.admin import (
    login_redirect,
    page_context,
    require_session,
    templates,
)
from app.web.admin_repository import WebAdminRepository
from app.web.admin_repository_stage27 import WebCrmRepository


router = APIRouter(prefix="/admin", include_in_schema=False)
settings = load_settings()


def make_client() -> ImpayaClient:
    return ImpayaClient(
        settings.impaya_api_url,
        settings.impaya_api_token,
        settings.impaya_binding_terminal_name or settings.impaya_terminal_name,
        auth_header=settings.impaya_auth_header,
        auth_prefix=settings.impaya_auth_prefix,
        protocol_version=settings.impaya_protocol_version,
        recurrent_terminal_name=(
            settings.impaya_recurrent_terminal_name
            or settings.impaya_terminal_name
        ),
    )


def back_to_user(user_id: int, *, message: str = "", level: str = "success"):
    query = urlencode({"notice": message, "notice_level": level}) if message else ""
    suffix = f"?{query}" if query else ""
    return RedirectResponse(
        f"/admin/crm/users/{user_id}{suffix}",
        status_code=303,
    )


async def load_entities(session, user_id: int):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    subscription = await session.scalar(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    method = await session.scalar(
        select(PaymentMethod).where(PaymentMethod.user_id == user_id)
    )
    return user, subscription, method


@router.get("/crm/users/{user_id}/control", response_class=HTMLResponse)
async def user_control(request: Request, user_id: int, action: str):
    admin_session = require_session(request)
    if admin_session is None:
        return login_redirect(request)

    allowed = {
        "charge_primary",
        "charge_fallback",
        "enable_auto_renew",
        "disable_auto_renew",
        "extend_1",
        "extend_3",
    }
    if action not in allowed:
        raise HTTPException(status_code=404, detail="Unknown action")

    async with SessionFactory() as session:
        user, subscription, method = await load_entities(session, user_id)

    labels = {
        "charge_primary": ("Списать 299 ₽", "Будет выполнено реальное MIT-списание по сохранённой карте."),
        "charge_fallback": ("Списать 99 ₽", "Будет выполнено реальное MIT-списание по сохранённой карте."),
        "enable_auto_renew": ("Включить автопродление", "Следующее списание будет назначено на дату окончания доступа или сейчас."),
        "disable_auto_renew": ("Отключить автопродление", "Оплаченный доступ сохранится до конца срока."),
        "extend_1": ("Продлить на 1 день", "Доступ будет выдан без списания денег."),
        "extend_3": ("Продлить на 3 дня", "Доступ будет выдан без списания денег."),
    }
    title, warning = labels[action]

    return templates.TemplateResponse(
        request=request,
        name="admin_action_confirm.html",
        context=page_context(
            request,
            title=title,
            section="users",
            user=user,
            subscription=subscription,
            payment_method=method,
            action=action,
            action_title=title,
            warning=warning,
        ),
    )


@router.post("/crm/users/{user_id}/control")
async def user_control_submit(
    request: Request,
    user_id: int,
    action: str = Form(...),
    confirmation: str = Form(...),
):
    admin_session = require_session(request)
    if admin_session is None:
        return login_redirect(request)

    if confirmation.strip().upper() != "ПОДТВЕРЖДАЮ":
        return back_to_user(
            user_id,
            message="Действие отменено: неверное подтверждение.",
            level="error",
        )

    client: ImpayaClient | None = None
    try:
        async with SessionFactory() as session:
            user, subscription, method = await load_entities(session, user_id)
            if subscription is None:
                return back_to_user(
                    user_id,
                    message="У пользователя нет подписки.",
                    level="error",
                )

            if action.startswith("charge_"):
                client = make_client()

            service = AdminSubscriptionControl(
                session,
                admin_username=admin_session.username,
                client=client,
                primary_amount=settings.primary_price_kopecks,
                fallback_amount=settings.fallback_price_kopecks,
                primary_days=settings.primary_duration_days,
                fallback_days=settings.fallback_duration_days,
            )

            if action == "charge_primary":
                result = await service.charge(subscription, method, plan="primary")
            elif action == "charge_fallback":
                result = await service.charge(subscription, method, plan="fallback")
            elif action == "enable_auto_renew":
                result = await service.set_auto_renew(subscription, enabled=True)
            elif action == "disable_auto_renew":
                result = await service.set_auto_renew(subscription, enabled=False)
            elif action == "extend_1":
                result = await service.extend_access(subscription, days=1)
            elif action == "extend_3":
                result = await service.extend_access(subscription, days=3)
            else:
                raise HTTPException(status_code=404, detail="Unknown action")

            if result.attempt_id is not None:
                return RedirectResponse(
                    f"/admin/payments/{result.attempt_id}"
                    f"?notice={urlencode({'x': result.message})[2:]}"
                    f"&notice_level={'success' if result.ok else 'error'}",
                    status_code=303,
                )

            return back_to_user(
                user_id,
                message=result.message,
                level="success" if result.ok else "error",
            )
    finally:
        if client is not None:
            await client.close()


@router.get("/subscriptions", response_class=HTMLResponse)
async def subscriptions(
    request: Request,
    q: str = "",
    status_filter: str = "",
    auto_renew: str = "",
    page: int = 0,
):
    if require_session(request) is None:
        return login_redirect(request)

    page = max(page, 0)
    page_size = 50
    filters = []
    cleaned = q.strip().lstrip("@")
    if cleaned:
        if cleaned.isdigit():
            numeric = int(cleaned)
            filters.append(or_(User.id == numeric, User.telegram_id == numeric))
        else:
            filters.append(User.username.ilike(f"%{cleaned}%"))

    if status_filter:
        filters.append(Subscription.status == status_filter)
    if auto_renew in {"yes", "no"}:
        filters.append(Subscription.auto_renew.is_(auto_renew == "yes"))

    async with SessionFactory() as session:
        total = int(
            await session.scalar(
                select(func.count(Subscription.id))
                .join(User, Subscription.user_id == User.id)
                .where(*filters)
            )
            or 0
        )
        result = await session.execute(
            select(Subscription, User, PaymentMethod)
            .join(User, Subscription.user_id == User.id)
            .outerjoin(PaymentMethod, PaymentMethod.user_id == User.id)
            .where(*filters)
            .order_by(Subscription.updated_at.desc(), Subscription.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        rows = result.all()

    return templates.TemplateResponse(
        request=request,
        name="subscriptions.html",
        context=page_context(
            request,
            title="Подписки",
            section="subscriptions",
            rows=rows,
            q=q,
            status_filter=status_filter,
            auto_renew=auto_renew,
            page=page,
            pages=max(ceil(total / page_size), 1),
            total=total,
        ),
    )


@router.get("/users/{user_id}", include_in_schema=False)
async def legacy_user_redirect(user_id: int):
    return RedirectResponse(f"/admin/crm/users/{user_id}", status_code=308)
