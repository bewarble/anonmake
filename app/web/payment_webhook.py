from __future__ import annotations

import hmac
from typing import Any

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.billing import PaymentAttempt
from app.models.reveal import RevealCheckout
from app.models.user import User
from app.services.impaya_factory import load_impaya_config
from app.services.payment_notifications import finalize_checkout_and_notify
from app.web.subscription_payments import finalize_subscription_payment

settings = load_settings()
WEBHOOK_PATH = "/payments/impaya/webhook"


class WebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    customer_operation_id: str | None = None
    transaction_id: str | None = None


async def _operation_id(payload: WebhookPayload, request: Request) -> str:
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
    return str(operation_id)


async def _owner_for_operation(session, operation_id: str) -> tuple[int, RevealCheckout | None]:
    checkout = await session.scalar(
        select(RevealCheckout).where(
            RevealCheckout.customer_operation_id == operation_id
        )
    )
    if checkout is not None:
        bot_id = await session.scalar(
            select(User.bot_id).where(User.id == checkout.buyer_id)
        )
        if bot_id is None:
            raise HTTPException(status_code=409, detail="Reveal checkout owner is missing")
        return int(bot_id), checkout

    bot_id = await session.scalar(
        select(PaymentAttempt.bot_id).where(
            PaymentAttempt.customer_operation_id == operation_id
        )
    )
    if bot_id is None:
        # Do not reveal whether an operation exists outside the platform. There
        # is no project secret that can safely authenticate an unknown operation.
        raise HTTPException(status_code=404, detail="Payment operation not found")
    return int(bot_id), None


def _verify_project_secret(received: str | None, expected: str) -> None:
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is disabled")
    expected = expected.strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Webhook secret is not configured")
    if received is None or not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


async def impaya_webhook(
    payload: WebhookPayload,
    request: Request,
    x_webhook_secret: str | None = Header(default=None),
) -> dict[str, str]:
    operation_id = await _operation_id(payload, request)

    async with SessionFactory() as session:
        bot_id, checkout = await _owner_for_operation(session, operation_id)
        config = await load_impaya_config(session, settings, bot_id)
        _verify_project_secret(x_webhook_secret, config.webhook_secret)

        if checkout is not None:
            # The finalizer intentionally resolves the owning project's bot and
            # payment client internally; compatibility parameters are ignored.
            locked = await session.scalar(
                select(RevealCheckout)
                .where(RevealCheckout.id == checkout.id)
                .with_for_update()
            )
            if locked is None:
                return {"status": "pending"}
            result = await finalize_checkout_and_notify(
                session,
                None,  # type: ignore[arg-type]
                None,  # type: ignore[arg-type]
                locked,
                payment_form_url_template="",
            )
            return {"status": result}

    result = await finalize_subscription_payment(operation_id, notify=True)
    return {"status": result}


def install_impaya_webhook(app) -> None:
    if getattr(app.state, "project_impaya_webhook_installed", False):
        return

    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == WEBHOOK_PATH
            and "POST" in (getattr(route, "methods", None) or set())
        )
    ]
    app.add_api_route(
        WEBHOOK_PATH,
        impaya_webhook,
        methods=["POST"],
        include_in_schema=True,
    )
    app.state.project_impaya_webhook_installed = True
