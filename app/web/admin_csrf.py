from __future__ import annotations

from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import PlainTextResponse

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
UNAUTHENTICATED_EXCEPTIONS = {"/admin/login"}


def _request_host(request: Request) -> str:
    return (request.headers.get("host") or "").strip().lower()


def _source_host(value: str) -> str:
    try:
        return urlparse(value).netloc.strip().lower()
    except ValueError:
        return ""


def same_origin_admin_request(request: Request) -> bool:
    """Require browser mutations to originate from the current admin host.

    Admin session cookies are already SameSite-protected, but critical project,
    credential and billing mutations must not rely on cookie policy alone. Modern
    browsers send Origin for unsafe form/fetch requests; Referer is accepted as a
    fallback for compatible deployments. Missing source metadata is rejected for
    authenticated admin mutations so a cross-site form cannot silently succeed.
    """
    if request.method.upper() not in UNSAFE_METHODS:
        return True
    if not request.url.path.startswith("/admin"):
        return True
    if request.url.path in UNAUTHENTICATED_EXCEPTIONS:
        return True

    host = _request_host(request)
    if not host:
        return False

    origin = (request.headers.get("origin") or "").strip()
    if origin:
        return _source_host(origin) == host

    referer = (request.headers.get("referer") or "").strip()
    if referer:
        return _source_host(referer) == host

    return False


def install_admin_csrf_guard(app) -> None:
    if getattr(app.state, "admin_csrf_guard_installed", False):
        return

    @app.middleware("http")
    async def admin_csrf_guard(request: Request, call_next):
        if not same_origin_admin_request(request):
            return PlainTextResponse("Invalid admin request origin", status_code=403)
        return await call_next(request)

    app.state.admin_csrf_guard_installed = True
