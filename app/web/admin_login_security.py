from __future__ import annotations

import hashlib

from fastapi import Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.redis_client import get_redis
from app.web.admin import auth, settings, templates
from app.web.admin_auth import COOKIE_NAME

LOGIN_PATH = "/admin/login"
WINDOW_SECONDS = 15 * 60
MAX_FAILURES_PER_USERNAME = 10
MAX_FAILURES_PER_IP = 30


def _client_ip(request: Request) -> str:
    # Do not trust X-Forwarded-For here unless the reverse proxy trust boundary
    # is explicitly configured. request.client cannot be forged by a remote
    # HTTP client even though multiple users behind one proxy may share it.
    return request.client.host if request.client is not None else "unknown"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _keys(request: Request, username: str) -> tuple[str, str]:
    normalized = username.strip().lower()
    return (
        f"admin-login:ip:{_digest(_client_ip(request))}",
        f"admin-login:user:{_digest(normalized)}",
    )


async def _redis():
    redis = get_redis(settings.redis_url)
    try:
        await redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin login protection is unavailable",
        ) from exc
    return redis


async def assert_login_allowed(request: Request, username: str) -> None:
    redis = await _redis()
    ip_key, user_key = _keys(request, username)
    ip_raw, user_raw = await redis.mget(ip_key, user_key)
    ip_failures = int(ip_raw or 0)
    user_failures = int(user_raw or 0)
    if ip_failures >= MAX_FAILURES_PER_IP or user_failures >= MAX_FAILURES_PER_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Повторите позже.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )


async def record_login_failure(request: Request, username: str) -> None:
    redis = await _redis()
    ip_key, user_key = _keys(request, username)
    pipe = redis.pipeline(transaction=True)
    for key in (ip_key, user_key):
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS, nx=True)
    await pipe.execute()


async def clear_login_success(username: str) -> None:
    redis = await _redis()
    user_key = f"admin-login:user:{_digest(username.strip().lower())}"
    await redis.delete(user_key)


async def secure_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/admin/business"),
):
    await assert_login_allowed(request, username)
    principal = await auth.verify_credentials(username, password)
    if principal is None:
        await record_login_failure(request, username)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "title": "Вход",
                "next": next if next.startswith("/admin") else "/admin/business",
                "error": "Неверный логин или пароль",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    await clear_login_success(username)
    destination = next if next.startswith("/admin") else "/admin/business"
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        auth.create_token(principal),
        max_age=settings.web_admin_session_minutes * 60,
        httponly=True,
        secure=settings.web_admin_secure_cookie,
        samesite="strict",
        path="/admin",
    )
    return response


def install_secure_admin_login(app) -> None:
    if getattr(app.state, "secure_admin_login_installed", False):
        return
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == LOGIN_PATH
            and "POST" in (getattr(route, "methods", None) or set())
        )
    ]
    app.add_api_route(
        LOGIN_PATH,
        secure_login_submit,
        methods=["POST"],
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    app.state.secure_admin_login_installed = True
