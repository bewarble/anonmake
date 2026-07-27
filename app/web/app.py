from __future__ import annotations

import hmac
import logging
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
            "<h1>Оплата подтверждена</h1>"
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
        "<h1>Оплата не завершена</h1>"
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
