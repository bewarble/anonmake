from __future__ import annotations

from fastapi import Request


async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )

    if request.url.path.startswith("/admin"):
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault(
            "Content-Security-Policy",
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )

    if request.url.scheme == "https":
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000",
        )

    return response


def install_security_headers(app) -> None:
    if getattr(app.state, "security_headers_installed", False):
        return
    app.middleware("http")(security_headers_middleware)
    app.state.security_headers_installed = True
