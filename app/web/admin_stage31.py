from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from math import ceil
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, or_, select

from app.core.bot_context import CurrentBot, reset_current_bot, set_current_bot
from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models import User
from app.models.billing import PaymentMethod, Subscription
from app.models.bot_instance import BotInstance
from app.services.admin_subscription_control import AdminSubscriptionControl
from app.services.impaya import ImpayaClient
from app.services.impaya_factory import create_impaya_client, load_impaya_config
from app.web.admin import (
    login_redirect,
    page_context,
    require_session,
    templates,
)


router = APIRouter(prefix="/admin", include_in_schema=False)
settings = load_settings()


def selected_bot_id(request: Request) -> int | None:
    scope = getattr(request.state, "admin_bot_scope", None)
    return getattr(scope, "bot_id", None)


@contextmanager
def bot_context(bot: BotInstance):
    token = set_current_bot(
        CurrentBot(bot.id, bot.code, bot.username, bot.display_name)
    )
    try:
        yield
    finally:
        reset_current_bot(token)


def back_to_user(user_id: int, *, message: str = "", level: str = "success"):
    query = urlencode({"notice": message, "notice_level": level}) if message else ""
    suffix = f"?{query}" if query else ""
    return RedirectResponse(
        f"/admin/crm/users/{user_id}{suffix}",
        status_code=303,
    )


async def load_entities(session, user_id: int, *, bot_id: int | None):
    filters = [User.id == user_id]
    if bot_id is not None:
        filters.append(User.bot_id == bot_id)
    user = await session.scalar(select(User).where(*filters))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    subscription = await session.scalar(
        select(Subscription).where(
            Subscription.bot_id == user.bot_id,
            Subscription.user_id == user.id,
        )
    )
    method = await session.scalar(
        select(PaymentMethod).where(
            PaymentMethod.bot_id == user.bot_id,
            PaymentMethod.user_id == user.id,
        )
    )
    bot = await session.get(BotInstance, user.bot_id)
    if bot is None:
        raise HTTPException(status_code=409, detail="Owning project is missing")
    return user, subscription, method, bot


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
        user, subscription, method, _ = await load_entities(
            session,
            user_id,
            bot_id=selected_bot_id(request),
        )

    labels = {
        "charge_primary": ("Списать 299 ₽", "Будет выполнено реальное MIT-списание по сохранённой карте."),
        "charge_fallback": ("Списать 99 ₽", "Будет выполнено реальное MIT-списание по сохранённой карте."),
        "enable_auto_renew": ("Включить автопродление", "Следующее списание будет назначено на дату окончания доступа или сейчас."),
        "disable_auto_renew": ("Отключить автопродление", "Оплаченный VIP статус сохранится до конца срока."),
        "extend_1": ("Продлить на 1 день", "VIP статус будет активирован без списания денег."),
        "extend_3": ("Продлить на 3 дня", "VIP статус будет активирован без списания денег."),
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
            user, subscription, method, owner_bot = await load_entities(
                session,
                user_id,
                bot_id=selected_bot_id(request),
            )
            if subscription is None:
                return back_to_user(
                    user_id,
                    message="У пользователя нет подписки.",
                    level="error",
                )

            if action.startswith("charge_"):
                config = await load_impaya_config(session, settings, owner_bot.id)
                client = create_impaya_client(config)

            service = AdminSubscriptionControl(
                session,
                admin_username=admin_session.username,
                client=client,
                primary_amount=settings.primary_price_kopecks,
                fallback_amount=settings.fallback_price_kopecks,
                primary_days=settings.primary_duration_days,
                fallback_days=settings.fallback_duration_days,
            )

            with bot_context(owner_bot):
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
    bot_id = selected_bot_id(request)
    filters = []
    if bot_id is not None:
        filters.extend((Subscription.bot_id == bot_id, User.bot_id == bot_id))
    cleaned = q.strip().lstrip("@")
    if cleaned:
        if cleaned.isdigit():
            numeric = int(cleaned)
            numeric_filters = [User.telegram_id == numeric]
            if -(2**31) <= numeric <= (2**31 - 1):
                numeric_filters.append(User.id == numeric)
            filters.append(or_(*numeric_filters))
        else:
            filters.append(User.username.ilike(f"%{cleaned}%"))

    if status_filter:
        filters.append(Subscription.status == status_filter)
    if auto_renew in {"yes", "no"}:
        filters.append(Subscription.auto_renew.is_(auto_renew == "yes"))

    async with SessionFactory() as session:
        base = (
            select(Subscription, User, PaymentMethod)
            .join(
                User,
                (Subscription.user_id == User.id)
                & (Subscription.bot_id == User.bot_id),
            )
            .outerjoin(
                PaymentMethod,
                (PaymentMethod.user_id == User.id)
                & (PaymentMethod.bot_id == User.bot_id),
            )
            .where(*filters)
        )
        total = int(
            await session.scalar(
                select(func.count()).select_from(base.subquery())
            )
            or 0
        )
        result = await session.execute(
            base.order_by(Subscription.updated_at.desc(), Subscription.id.desc())
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
