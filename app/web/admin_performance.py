from __future__ import annotations

import os
from pathlib import Path
import resource

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select, text

from app.database.session import SessionFactory
from app.models.billing import PaymentAttempt, Subscription
from app.models.delivery import DeliveryOutbox
from app.models.marketing import Broadcast
from app.models.user import User
from app.web.admin import (
    login_redirect,
    page_context,
    require_session,
    templates,
)

router = APIRouter(prefix="/admin", include_in_schema=False)


def _memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if os.uname().sysname == "Darwin":
        return round(value / 1024 / 1024, 1)
    return round(value / 1024, 1)


@router.get("/performance", response_class=HTMLResponse)
async def performance_dashboard(request: Request):
    if require_session(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        database_size = await session.scalar(
            text("SELECT pg_database_size(current_database())")
        )
        delivery = dict(
            (
                await session.execute(
                    select(DeliveryOutbox.status, func.count(DeliveryOutbox.id))
                    .group_by(DeliveryOutbox.status)
                )
            ).all()
        )
        broadcasts = dict(
            (
                await session.execute(
                    select(Broadcast.status, func.count(Broadcast.id))
                    .group_by(Broadcast.status)
                )
            ).all()
        )
        users = int(await session.scalar(select(func.count(User.id))) or 0)
        active_vip = int(
            await session.scalar(
                select(func.count(Subscription.id)).where(
                    Subscription.access_until.is_not(None),
                    Subscription.access_until > func.now(),
                )
            )
            or 0
        )
        pending_payments = int(
            await session.scalar(
                select(func.count(PaymentAttempt.id)).where(
                    PaymentAttempt.status == "pending"
                )
            )
            or 0
        )

    load = os.getloadavg()
    snapshot = {
        "load_1": round(load[0], 2),
        "load_5": round(load[1], 2),
        "load_15": round(load[2], 2),
        "memory_mb": _memory_mb(),
        "database_mb": round(int(database_size or 0) / 1024 / 1024, 1),
        "users": users,
        "active_vip": active_vip,
        "pending_payments": pending_payments,
        "delivery_pending": int(delivery.get("pending", 0)) + int(delivery.get("retry", 0)),
        "delivery_failed": int(delivery.get("failed", 0)),
        "broadcast_queued": int(broadcasts.get("queued", 0)) + int(broadcasts.get("running", 0)),
    }
    return templates.TemplateResponse(
        request=request,
        name="performance.html",
        context=page_context(
            request,
            title="Производительность",
            section="performance",
            snapshot=snapshot,
        ),
    )
