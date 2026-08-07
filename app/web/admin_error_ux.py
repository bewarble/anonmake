from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path
from urllib.parse import urlencode

from fastapi import HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.admin import AdminAuditLog
from app.web.admin_auth import AdminAuth

logger = logging.getLogger(__name__)
settings = load_settings()
auth = AdminAuth(settings)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

ERROR_TITLES = {
    403: "Доступ запрещён",
    404: "Страница не найдена",
    409: "Конфликт изменений",
    422: "Проверьте введённые данные",
    500: "Ошибка сервера",
}
ERROR_MESSAGES = {
    403: "У вас нет доступа к этому разделу или проекту.",
    404: "Такой страницы больше нет или адрес указан неверно.",
    409: "Состояние данных изменилось. Обновите страницу и повторите действие.",
    422: "Некоторые данные формы не прошли проверку. Исправьте значения и повторите действие.",
    500: "Мы зарегистрировали ошибку. Передайте идентификатор администратору для диагностики.",
}


def new_error_id() -> str:
    return f"err_{secrets.token_hex(6)}"


def is_admin_request(request: Request) -> bool:
    return request.url.path.startswith("/admin") and not request.url.path.startswith("/admin/static")


def flash_from_request(request: Request) -> dict[str, str] | None:
    message = request.query_params.get("flash")
    if not message:
        return None
    tone = request.query_params.get("flash_tone", "success")
    if tone not in {"success", "warning", "danger", "info"}:
        tone = "info"
    return {"message": message[:240], "tone": tone}


def redirect_with_flash(url: str, message: str, *, tone: str = "success") -> RedirectResponse:
    separator = "&" if "?" in url else "?"
    query = urlencode({"flash": message[:240], "flash_tone": tone})
    return RedirectResponse(f"{url}{separator}{query}", status_code=303)


def decode_error_event(row: AdminAuditLog) -> dict:
    try:
        details = json.loads(row.details or "{}")
    except (TypeError, json.JSONDecodeError):
        details = {}
    return {
        "error_id": row.target or "—",
        "created_at": row.created_at,
        "status": details.get("status"),
        "route": details.get("route") or "—",
        "method": details.get("method") or "—",
        "admin": details.get("admin") or "—",
        "project": details.get("project") or "—",
    }


async def record_admin_error(request: Request, *, error_id: str, status_code: int) -> None:
    principal = auth.session_from_request(request)
    scope = getattr(request.state, "admin_bot_scope", None)
    details = {
        "status": status_code,
        "method": request.method,
        "route": request.url.path[:500],
        "admin": principal.username[:200] if principal else None,
        "admin_id": principal.admin_id if principal else None,
        "project": getattr(scope, "code", None),
        "project_id": getattr(scope, "bot_id", None),
    }
    try:
        async with SessionFactory() as session:
            session.add(
                AdminAuditLog(
                    admin_telegram_id=(principal.admin_id if principal and principal.admin_id else 0),
                    action="web_error",
                    target=error_id,
                    details=json.dumps(details, ensure_ascii=False, separators=(",", ":")),
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Could not persist admin error event error_id=%s", error_id)


async def render_admin_error(
    request: Request,
    *,
    status_code: int,
    error_id: str | None = None,
    log_event: bool = True,
):
    normalized = status_code if status_code in ERROR_TITLES else 500
    error_id = error_id or new_error_id()
    if log_event:
        await record_admin_error(request, error_id=error_id, status_code=normalized)
    return templates.TemplateResponse(
        request=request,
        name="admin_error.html",
        context={
            "title": ERROR_TITLES[normalized],
            "status_code": normalized,
            "error_id": error_id,
            "message": ERROR_MESSAGES[normalized],
            "show_error_id": normalized >= 500,
        },
        status_code=normalized,
    )


async def admin_http_exception_handler(request: Request, exc: HTTPException):
    if not is_admin_request(request):
        return await http_exception_handler(request, exc)
    status_code = exc.status_code if exc.status_code in ERROR_TITLES else (500 if exc.status_code >= 500 else 404)
    return await render_admin_error(request, status_code=status_code)


async def admin_validation_exception_handler(request: Request, exc: RequestValidationError):
    if not is_admin_request(request):
        return await request_validation_exception_handler(request, exc)
    return await render_admin_error(request, status_code=422)


async def admin_unhandled_exception_handler(request: Request, exc: Exception):
    if not is_admin_request(request):
        logger.exception("Unhandled web error", exc_info=exc)
        return JSONResponse({"detail": "Internal Server Error"}, status_code=500)
    error_id = new_error_id()
    logger.exception("Unhandled admin error error_id=%s path=%s", error_id, request.url.path, exc_info=exc)
    return await render_admin_error(request, status_code=500, error_id=error_id)
