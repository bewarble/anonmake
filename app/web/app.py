from __future__ import annotations

import hmac
import logging
import time
from pathlib import Path
from typing import Any

from aiogram import Bot
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.core.config import load_settings
from app.core.performance import (
    observe_operation,
    reset_request_sql_stats,
    restore_request_sql_stats,
)
from app.database.session import (
    SessionFactory,
    close_database,
    engine,
    init_database,
)
from app.repositories.reveals import RevealRepository
from app.services.impaya import ImpayaClient
from app.services.payment_notifications import finalize_checkout_and_notify
from app.web.subscription_payments import finalize_subscription_payment


logger = logging.getLogger(__name__)
settings = load_settings()
WEB_DIR = Path(__file__).resolve().parent

app = FastAPI(title="AnonMake", version="26.1")
app.mount(
    "/admin/static",
    StaticFiles(directory=str(WEB_DIR / "static")),
    name="admin-static",
)


@app.middleware("http")
async def admin_bot_scope_middleware(request: Request, call_next):
    if not request.url.path.startswith("/admin") or request.url.path.startswith("/admin/static"):
        return await call_next(request)

    from app.web.admin_scope import COOKIE_NAME, load_admin_bot_scope

    scope = await load_admin_bot_scope(request)
    request.state.admin_bot_scope = scope
    if scope.denied:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("Доступ к проекту запрещён", status_code=403)
    response = await call_next(request)

    requested = request.query_params.get("bot")
    if requested is not None:
        response.set_cookie(
            COOKIE_NAME,
            scope.code,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            secure=settings.web_admin_secure_cookie,
            samesite="lax",
            path="/admin",
        )
    return response


@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    if not settings.performance_enabled:
        return await call_next(request)

    tokens = reset_request_sql_stats()
    started = time.perf_counter()
    status = "ok"
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            status = "error"
        return response
    except Exception:
        status = "error"
        raise
    finally:
        observe_operation(
            component="web",
            operation=request.url.path,
            status=status,
            started=started,
            slow_ms=settings.performance_slow_operation_ms,
            profile_enabled=settings.performance_profile_enabled,
        )
        restore_request_sql_stats(tokens)


class WebhookPayload(BaseModel):
    """Tolerant callback payload; transaction state is verified with Impaya."""

    model_config = ConfigDict(extra="allow")

    customer_operation_id: str | None = None
    transaction_id: str | None = None


def make_impaya_client() -> ImpayaClient:
    return ImpayaClient(
        settings.impaya_api_url,
        settings.impaya_api_token,
        (
            settings.impaya_binding_terminal_name
            or settings.impaya_terminal_name
        ),
        auth_header=settings.impaya_auth_header,
        auth_prefix=settings.impaya_auth_prefix,
        protocol_version=settings.impaya_protocol_version,
        recurrent_terminal_name=(
            settings.impaya_recurrent_terminal_name
            or settings.impaya_terminal_name
        ),
    )


def verify_webhook_secret(received: str | None) -> None:
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is disabled")

    expected = settings.impaya_webhook_secret.strip()
    if expected and (
        received is None
        or not hmac.compare_digest(received, expected)
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@app.on_event("startup")
async def startup() -> None:
    await init_database()


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_database()


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    try:
        async with engine.connect() as connection:
            value = await connection.scalar(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database healthcheck failed")
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from exc

    if value != 1:
        raise HTTPException(status_code=503, detail="Database unhealthy")
    return {"status": "ok"}


async def process_checkout(checkout_token: str) -> str:
    bot = Bot(token=settings.require_bot_token())
    client = make_impaya_client()
    try:
        async with SessionFactory() as session:
            checkout = await RevealRepository(session).get_by_token(
                checkout_token,
                for_update=True,
            )
            if checkout is None:
                return "not_found"

            return await finalize_checkout_and_notify(
                session,
                bot,
                client,
                checkout,
                payment_form_url_template=(
                    settings.impaya_payment_form_url_template
                ),
            )
    finally:
        await client.close()
        await bot.session.close()


@app.get(
    "/payments/return/success/{checkout_token}",
    response_class=HTMLResponse,
)
async def payment_success(checkout_token: str) -> HTMLResponse:
    result = await process_checkout(checkout_token)

    if result in {"notified", "already_notified"}:
        body = (
            "<h1>✅ Всё готово!</h1><p>Вернитесь в Telegram — VIP статус уже активирован.</p>"
            "<p>VIP активирован. Результат отправлен в Telegram.</p>"
        )
    elif result == "pending":
        body = (
            "<h1>Платёж обрабатывается</h1>"
            "<p>Бот автоматически пришлёт результат после подтверждения.</p>"
        )
    else:
        body = (
            "<h1>Не удалось завершить обработку</h1>"
            "<p>Вернитесь в Telegram. Система продолжит сверку платежа.</p>"
        )

    return HTMLResponse(
        "<!doctype html><html lang='ru'><meta charset='utf-8'>"
        f"<title>AnonMake</title><body>{body}</body></html>"
    )


@app.get(
    "/payments/return/fail/{checkout_token}",
    response_class=HTMLResponse,
)
async def payment_fail(checkout_token: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html lang='ru'><meta charset='utf-8'>"
        "<title>AnonMake</title><body>"
        "<h1>❌ Оплата не завершена</h1><p>Вернитесь в Telegram и попробуйте ещё раз.</p>"
        "<p>Закройте страницу и повторите попытку в Telegram.</p>"
        "</body></html>"
    )


@app.post("/payments/impaya/webhook")
async def impaya_webhook(
    payload: WebhookPayload,
    request: Request,
    x_webhook_secret: str | None = Header(default=None),
) -> dict[str, str]:
    verify_webhook_secret(x_webhook_secret)

    operation_id = payload.customer_operation_id
    if not operation_id:
        raw: dict[str, Any] = await request.json()
        transaction = raw.get("transaction") or {}
        operation_id = (
            raw.get("customer_operation_id")
            or transaction.get("customer_operation_id")
        )

    if not operation_id:
        raise HTTPException(
            status_code=422,
            detail="customer_operation_id is required",
        )

    bot = Bot(token=settings.require_bot_token())
    client = make_impaya_client()
    try:
        async with SessionFactory() as session:
            checkout = await RevealRepository(
                session
            ).get_by_customer_operation_id(
                str(operation_id),
                for_update=True,
            )
            if checkout is None:
                result = await finalize_subscription_payment(
                    str(operation_id),
                    notify=True,
                )
                return {"status": result}

            result = await finalize_checkout_and_notify(
                session,
                bot,
                client,
                checkout,
                payment_form_url_template=(
                    settings.impaya_payment_form_url_template
                ),
            )
            return {"status": result}
    finally:
        await client.close()
        await bot.session.close()

# Begin Stage 30 subscription payment routes.
from app.web import subscription_payments as subscription_payments_module  # noqa: E402

for subscription_payment_route in subscription_payments_module.router.routes:
    route_path = getattr(subscription_payment_route, "path", None)
    route_methods = getattr(subscription_payment_route, "methods", None)
    if not any(
        getattr(existing, "path", None) == route_path
        and getattr(existing, "methods", None) == route_methods
        for existing in app.router.routes
    ):
        app.router.routes.append(subscription_payment_route)
# End Stage 30 subscription payment routes.

# Register the admin router after all modules and routes are initialized.


# Import the completed admin module only after the main application
# and payment routes have been declared.
from app.web import admin as admin_module  # noqa: E402

# APIRouter routes are copied explicitly to avoid circular-import timing.
for admin_route in admin_module.router.routes:
    if admin_route not in app.router.routes:
        app.router.routes.append(admin_route)
# Stage 27 CRM routes.


# Register completed Stage 27 CRM routes.
from app.web import admin_stage27 as admin_stage27_module  # noqa: E402

for crm_route in admin_stage27_module.router.routes:
    if not any(
        getattr(existing, 'path', None) == getattr(crm_route, 'path', None)
        and getattr(existing, 'methods', None) == getattr(crm_route, 'methods', None)
        for existing in app.router.routes
    ):
        app.router.routes.append(crm_route)
# End Stage 27 CRM routes.
# Stage 28 professional web admin.


# Begin Stage 28 route registration.
from app.web import admin_stage28 as admin_stage28_module  # noqa: E402

for stage28_route in admin_stage28_module.router.routes:
    stage28_path = getattr(stage28_route, 'path', None)
    stage28_methods = getattr(stage28_route, 'methods', None)

    already_registered = any(
        getattr(existing, 'path', None) == stage28_path
        and getattr(existing, 'methods', None) == stage28_methods
        for existing in app.router.routes
    )

    if not already_registered:
        app.router.routes.append(stage28_route)
# End Stage 28 route registration.

# Begin Stage 28.1 route registration.
from app.web import admin_stage28_1 as admin_stage28_1_module  # noqa: E402

for stage28_1_route in admin_stage28_1_module.router.routes:
    route_path = getattr(stage28_1_route, "path", None)
    route_methods = getattr(stage28_1_route, "methods", None)
    if not any(
        getattr(existing, "path", None) == route_path
        and getattr(existing, "methods", None) == route_methods
        for existing in app.router.routes
    ):
        app.router.routes.append(stage28_1_route)
# End Stage 28.1 route registration.

# Begin Stage 29 route registration.
from app.web import admin_stage29 as admin_stage29_module  # noqa: E402
for stage29_route in admin_stage29_module.router.routes:
    path = getattr(stage29_route, "path", None)
    methods = getattr(stage29_route, "methods", None)
    if not any(
        getattr(existing, "path", None) == path
        and getattr(existing, "methods", None) == methods
        for existing in app.router.routes
    ):
        app.router.routes.append(stage29_route)
# End Stage 29 route registration.

# Begin Stage 29.3 route registration.
from app.web import admin_stage29_3 as admin_stage29_3_module  # noqa: E402

for stage29_3_route in admin_stage29_3_module.router.routes:
    route_path = getattr(stage29_3_route, "path", None)
    route_methods = getattr(stage29_3_route, "methods", None)
    if not any(
        getattr(existing, "path", None) == route_path
        and getattr(existing, "methods", None) == route_methods
        for existing in app.router.routes
    ):
        app.router.routes.append(stage29_3_route)
# End Stage 29.3 route registration.



# Begin Stage 31 Admin Control Center registration.
from app.web import admin_stage31 as admin_stage31_module  # noqa: E402

stage31_existing = {
    (
        getattr(route, "path", None),
        frozenset(getattr(route, "methods", None) or ()),
    )
    for route in app.router.routes
}
for stage31_route in admin_stage31_module.router.routes:
    stage31_key = (
        getattr(stage31_route, "path", None),
        frozenset(getattr(stage31_route, "methods", None) or ()),
    )
    if stage31_key not in stage31_existing:
        app.router.routes.append(stage31_route)
        stage31_existing.add(stage31_key)
# End Stage 31 Admin Control Center registration.


# Stage 35.2 product completeness routes.
from app.web import admin_complete as admin_complete_module  # noqa: E402

existing_complete_routes = {
    (
        getattr(route, "path", None),
        frozenset(getattr(route, "methods", None) or ()),
    )
    for route in app.router.routes
}
for complete_route in admin_complete_module.router.routes:
    complete_key = (
        getattr(complete_route, "path", None),
        frozenset(getattr(complete_route, "methods", None) or ()),
    )
    if complete_key not in existing_complete_routes:
        app.router.routes.append(complete_route)
        existing_complete_routes.add(complete_key)


# Stage 39 performance dashboard.
from app.web import admin_performance as admin_performance_module  # noqa: E402

for performance_route in admin_performance_module.router.routes:
    if not any(
        getattr(existing, "path", None) == getattr(performance_route, "path", None)
        and getattr(existing, "methods", None) == getattr(performance_route, "methods", None)
        for existing in app.router.routes
    ):
        app.router.routes.append(performance_route)


# Stage 40 multibot admin control center.
from app.web import admin_multibot as admin_multibot_module  # noqa: E402

for multibot_route in admin_multibot_module.router.routes:
    if not any(
        getattr(existing, "path", None) == getattr(multibot_route, "path", None)
        and getattr(existing, "methods", None) == getattr(multibot_route, "methods", None)
        for existing in app.router.routes
    ):
        app.router.routes.append(multibot_route)


# Stage 41 platform administration.
from app.web import admin_platform as admin_platform_module  # noqa: E402

for platform_route in admin_platform_module.router.routes:
    if not any(
        getattr(existing, "path", None) == getattr(platform_route, "path", None)
        and getattr(existing, "methods", None) == getattr(platform_route, "methods", None)
        for existing in app.router.routes
    ):
        app.router.routes.append(platform_route)


# Stage 45 project creation wizard.
from app.web import admin_project_wizard as admin_project_wizard_module  # noqa: E402

for wizard_route in admin_project_wizard_module.router.routes:
    if not any(getattr(existing, "path", None) == getattr(wizard_route, "path", None) and getattr(existing, "methods", None) == getattr(wizard_route, "methods", None) for existing in app.router.routes):
        app.router.routes.append(wizard_route)


# Stage 47 platform system operations.
from app.web import admin_system as admin_system_module  # noqa: E402

for system_route in admin_system_module.router.routes:
    if not any(
        getattr(existing, "path", None) == getattr(system_route, "path", None)
        and getattr(existing, "methods", None) == getattr(system_route, "methods", None)
        for existing in app.router.routes
    ):
        app.router.routes.append(system_route)
