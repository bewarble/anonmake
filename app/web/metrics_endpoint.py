from __future__ import annotations

import hmac

from fastapi import Header, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import load_settings

METRICS_PATH = "/metrics"
settings = load_settings()


def _verify_metrics_token(received: str | None) -> None:
    expected = settings.metrics_token.strip()
    if not expected:
        raise HTTPException(status_code=404, detail="Not found")
    if received is None or not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Invalid metrics token")


async def metrics(x_metrics_token: str | None = Header(default=None)) -> Response:
    _verify_metrics_token(x_metrics_token)
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


def install_metrics_endpoint(app) -> None:
    if getattr(app.state, "protected_metrics_endpoint_installed", False):
        return

    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == METRICS_PATH
            and "GET" in (getattr(route, "methods", None) or set())
        )
    ]
    app.add_api_route(
        METRICS_PATH,
        metrics,
        methods=["GET"],
        include_in_schema=False,
    )
    app.state.protected_metrics_endpoint_installed = True
