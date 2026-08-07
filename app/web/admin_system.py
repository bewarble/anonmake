from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select, text

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.billing import PaymentAttempt
from app.models.delivery import DeliveryOutbox
from app.models.marketing import Broadcast
from app.services.redis_client import get_redis
from app.web.admin import login_redirect, page_context, require_session, templates

router = APIRouter(prefix="/admin/platform", include_in_schema=False)
settings = load_settings()
ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT / "var" / "deploy-state.json"
BACKUP_DIR = ROOT / "backups" / "deploy"
POSTGRES_CUSTOM_MAGIC = b"PGDMP"


def _load_deploy_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _source_head() -> str:
    try:
        script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
        return ", ".join(script.get_heads())
    except Exception:
        return "Не определена"


def _backup_is_valid(path: Path) -> bool:
    try:
        if path.stat().st_size <= len(POSTGRES_CUSTOM_MAGIC):
            return False
        with path.open("rb") as stream:
            return stream.read(len(POSTGRES_CUSTOM_MAGIC)) == POSTGRES_CUSTOM_MAGIC
    except OSError:
        return False


def _backups(limit: int = 8) -> list[dict]:
    try:
        files = sorted(
            BACKUP_DIR.glob("*.dump"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return []

    result: list[dict] = []
    for path in files[:limit]:
        try:
            stat = path.stat()
        except OSError:
            continue
        result.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                "valid": _backup_is_valid(path),
            }
        )
    return result


def _last_backup() -> dict | None:
    backups = _backups(limit=1)
    return backups[0] if backups else None


@router.get("/system", response_class=HTMLResponse)
async def system_page(request: Request):
    principal = require_session(request)
    if principal is None:
        return login_redirect(request)
    if not principal.is_superadmin:
        raise HTTPException(status_code=403, detail="Раздел доступен только суперадминистратору")

    postgres_ok = False
    redis_ok = False
    database_head = "Не определена"
    queues = {"delivery": 0, "broadcasts": 0, "payments": 0}

    try:
        async with SessionFactory() as session:
            postgres_ok = bool(await session.scalar(text("SELECT TRUE")))
            database_head = str(
                await session.scalar(text("SELECT version_num FROM alembic_version"))
                or "Не определена"
            )
            queues["delivery"] = int(
                await session.scalar(
                    select(func.count(DeliveryOutbox.id)).where(
                        DeliveryOutbox.status.in_(("pending", "processing"))
                    )
                )
                or 0
            )
            queues["broadcasts"] = int(
                await session.scalar(
                    select(func.count(Broadcast.id)).where(
                        Broadcast.status.in_(("scheduled", "processing"))
                    )
                )
                or 0
            )
            queues["payments"] = int(
                await session.scalar(
                    select(func.count(PaymentAttempt.id)).where(
                        PaymentAttempt.status == "pending"
                    )
                )
                or 0
            )
    except Exception:
        postgres_ok = False

    try:
        redis = get_redis(settings.redis_url)
        redis_ok = bool(await redis.ping())
    except Exception:
        redis_ok = False

    state = _load_deploy_state()
    backups = _backups()
    return templates.TemplateResponse(
        request=request,
        name="platform_system.html",
        context=page_context(
            request,
            title="Система",
            section="platform_system",
            postgres_ok=postgres_ok,
            redis_ok=redis_ok,
            source_head=_source_head(),
            database_head=database_head,
            deploy=state,
            services=state.get("services", {}),
            queues=queues,
            last_backup=backups[0] if backups else None,
            backups=backups,
            backup_count=len(backups),
        ),
    )


# Stage 48 observability routes share the platform operations registration point.
from app.web import admin_observability as admin_observability_module  # noqa: E402

for observability_route in admin_observability_module.router.routes:
    if not any(
        getattr(existing, "path", None) == getattr(observability_route, "path", None)
        and getattr(existing, "methods", None) == getattr(observability_route, "methods", None)
        for existing in router.routes
    ):
        router.routes.append(observability_route)
