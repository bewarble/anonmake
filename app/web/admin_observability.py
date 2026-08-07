from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select, update

from app.core.error_diagnostics import decode_bot_error_event
from app.core.platform_health import overall_runtime_status, runtime_health_snapshot
from app.database.session import SessionFactory
from app.models.admin import AdminAuditLog
from app.models.billing import PaymentAttempt
from app.models.bot_instance import BotInstance
from app.models.delivery import DeliveryOutbox
from app.web.admin import login_redirect, page_context, require_session, templates
from app.web.admin_error_ux import decode_error_event, redirect_with_flash

router = APIRouter(prefix="/admin/platform", include_in_schema=False)
ROOT = Path(__file__).resolve().parents[2]
DEPLOY_HISTORY = ROOT / "var" / "deploy-history.jsonl"


def require_superadmin(request: Request):
    principal = require_session(request)
    if principal is None:
        return None
    if not principal.is_superadmin:
        raise HTTPException(
            status_code=403,
            detail="Раздел доступен только суперадминистратору",
        )
    return principal


def _failed_deploys(limit: int = 20) -> list[dict]:
    try:
        lines = DEPLOY_HISTORY.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    failures: list[dict] = []
    for line in reversed(lines):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("status") != "success":
            failures.append(item)
        if len(failures) >= limit:
            break
    return failures


@router.get("/observability", response_class=HTMLResponse)
async def observability_page(request: Request):
    if require_superadmin(request) is None:
        return login_redirect(request)

    runtime_health = runtime_health_snapshot()
    runtime_status = overall_runtime_status(runtime_health)

    async with SessionFactory() as session:
        bots = list((await session.execute(select(BotInstance).order_by(BotInstance.id))).scalars())
        bot_names = {bot.id: bot.display_name for bot in bots}

        status_rows = await session.execute(
            select(DeliveryOutbox.status, func.count(DeliveryOutbox.id))
            .group_by(DeliveryOutbox.status)
            .order_by(DeliveryOutbox.status)
        )
        delivery_counts = {status: int(count) for status, count in status_rows}

        oldest_pending = await session.scalar(
            select(func.min(DeliveryOutbox.created_at)).where(
                DeliveryOutbox.status.in_(("pending", "processing"))
            )
        )

        failed_deliveries = list(
            (
                await session.execute(
                    select(DeliveryOutbox)
                    .where(DeliveryOutbox.status == "failed")
                    .order_by(DeliveryOutbox.updated_at.desc())
                    .limit(30)
                )
            ).scalars()
        )

        payment_errors = list(
            (
                await session.execute(
                    select(PaymentAttempt)
                    .where(PaymentAttempt.error_message.is_not(None))
                    .order_by(PaymentAttempt.created_at.desc())
                    .limit(30)
                )
            ).scalars()
        )

        web_error_rows = list(
            (
                await session.execute(
                    select(AdminAuditLog)
                    .where(AdminAuditLog.action == "web_error")
                    .order_by(AdminAuditLog.created_at.desc())
                    .limit(30)
                )
            ).scalars()
        )
        recent_admin_errors = [decode_error_event(row) for row in web_error_rows]

        bot_error_rows = list(
            (
                await session.execute(
                    select(AdminAuditLog)
                    .where(AdminAuditLog.action == "bot_error")
                    .order_by(AdminAuditLog.created_at.desc())
                    .limit(50)
                )
            ).scalars()
        )
        recent_bot_errors = [decode_bot_error_event(row) for row in bot_error_rows]

    incident_count = sum(row.status != "healthy" for row in runtime_health)
    incident_count += int(delivery_counts.get("failed", 0) > 0)
    incident_count += int(bool(recent_bot_errors))

    return templates.TemplateResponse(
        request=request,
        name="platform_observability.html",
        context=page_context(
            request,
            title="Наблюдаемость",
            section="platform_observability",
            runtime_health=runtime_health,
            runtime_status=runtime_status,
            incident_count=incident_count,
            delivery_counts=delivery_counts,
            oldest_pending=oldest_pending,
            failed_deliveries=failed_deliveries,
            payment_errors=payment_errors,
            failed_deploys=_failed_deploys(),
            recent_admin_errors=recent_admin_errors,
            recent_bot_errors=recent_bot_errors,
            bot_names=bot_names,
        ),
    )


@router.post("/observability/delivery/{job_id}/retry")
async def retry_delivery(request: Request, job_id: int):
    if require_superadmin(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        job = await session.get(DeliveryOutbox, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Задание доставки не найдено")
        if job.status != "failed":
            raise HTTPException(
                status_code=409,
                detail="Повтор доступен только для неудачных заданий",
            )
        job.status = "pending"
        job.attempts = 0
        job.next_attempt_at = None
        job.locked_at = None
        job.locked_by = None
        job.last_error = None
        await session.commit()

    return redirect_with_flash(
        "/admin/platform/observability",
        "Задание доставки возвращено в очередь.",
    )


@router.post("/observability/delivery/unlock-stale")
async def unlock_stale_deliveries(request: Request):
    if require_superadmin(request) is None:
        return login_redirect(request)

    threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    async with SessionFactory() as session:
        result = await session.execute(
            update(DeliveryOutbox)
            .where(
                DeliveryOutbox.status == "processing",
                DeliveryOutbox.locked_at.is_not(None),
                DeliveryOutbox.locked_at < threshold,
            )
            .values(
                status="pending",
                locked_at=None,
                locked_by=None,
                next_attempt_at=None,
            )
        )
        await session.commit()
        count = int(result.rowcount or 0)

    return redirect_with_flash(
        "/admin/platform/observability",
        f"Освобождено зависших доставок: {count}.",
        tone="success" if count else "info",
    )
