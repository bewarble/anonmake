from __future__ import annotations

from collections.abc import Iterable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute


def route_key(route: BaseRoute) -> tuple[str | None, frozenset[str]]:
    return (
        getattr(route, "path", None),
        frozenset(getattr(route, "methods", None) or ()),
    )


def register_unique_routes(
    app: FastAPI,
    routes: Iterable[BaseRoute],
) -> int:
    """Register routes without duplicating an existing path/method pair."""
    existing = {route_key(route) for route in app.router.routes}
    registered = 0

    for route in routes:
        key = route_key(route)
        if key in existing:
            continue
        app.router.routes.append(route)
        existing.add(key)
        registered += 1

    return registered
