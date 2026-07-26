from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi.responses import Response

import hmac
import logging
from typing import Any

from aiogram import Bot
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict

from app.core.config import load_settings
from app.database.session import SessionFactory, close_database, init_database
from app.repositories.reveals import RevealRepository
from app.services.impaya import ImpayaClient
from app.services.payment_notifications import finalize_checkout_and_notify

logger = logging.getLogger(__name__)
settings = load_settings()
app = FastAPI(title="AnonMake payments", version="5.2")


class WebhookPayload(BaseModel):
    """Tolerant payload model.

    Impaya callback fields can evolve. We only use identifiers to locate the
    checkout, then obtain the authoritative transaction state from Impaya.
    """

    model_config = ConfigDict(extra="allow")

    customer_operation_id: str | None = None
    transaction_id: str | None = None


def make_impaya_client() -> ImpayaClient:
    return ImpayaClient(
        settings.impaya_api_url,
        settings.impaya_api_token,
        settings.impaya_terminal_name,
        auth_header=settings.impaya_auth_header,
        auth_prefix=settings.impaya_auth_prefix,
        protocol_version=settings.impaya_protocol_version,
    )


def verify_webhook_secret(received: str | None) -> None:
    expected = settings.impaya_webhook_secret
    if not expected:
        return
    if received is None or not hmac.compare_digest(received, expected):
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
            "<p>VIP активирован. Отправитель уже отправлен вам в Telegram.</p>"
        )
    elif result == "pending":
        body = (
            "<h1>Платёж обрабатывается</h1>"
            "<p>Бот автоматически пришлёт результат после подтверждения оплаты.</p>"
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
        "<p>Вы можете закрыть страницу и повторить попытку в Telegram.</p>"
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
                # Unknown notifications are acknowledged so provider retries do
                # not create an endless loop.
                return {"status": "ignored"}

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
