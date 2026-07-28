from __future__ import annotations

from contextvars import ContextVar
import logging
import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

OPERATION_SECONDS = Histogram(
    "anonmake_operation_seconds",
    "Application operation duration",
    ("component", "operation", "bot_code", "status"),
)
SQL_SECONDS = Histogram(
    "anonmake_sql_seconds",
    "SQL query duration",
    ("statement",),
)
SQL_QUERIES = Counter(
    "anonmake_sql_queries_total",
    "SQL query count",
    ("statement",),
)
SLOW_OPERATIONS = Counter(
    "anonmake_slow_operations_total",
    "Operations exceeding the configured threshold",
    ("component", "operation"),
)
WORKER_BATCHES = Counter(
    "anonmake_worker_batches_total",
    "Worker batches",
    ("worker", "result"),
)
WORKER_BATCH_SIZE = Histogram(
    "anonmake_worker_batch_size",
    "Items processed per worker batch",
    ("worker",),
)
WORKER_IDLE_SECONDS = Gauge(
    "anonmake_worker_idle_seconds",
    "Current adaptive worker idle delay",
    ("worker",),
)

_sql_count: ContextVar[int] = ContextVar("performance_sql_count", default=0)
_sql_seconds: ContextVar[float] = ContextVar(
    "performance_sql_seconds",
    default=0.0,
)


def reset_request_sql_stats() -> tuple[Any, Any]:
    return _sql_count.set(0), _sql_seconds.set(0.0)


def restore_request_sql_stats(tokens: tuple[Any, Any]) -> None:
    _sql_count.reset(tokens[0])
    _sql_seconds.reset(tokens[1])


def request_sql_stats() -> tuple[int, float]:
    return _sql_count.get(), _sql_seconds.get()


def record_sql(statement: str, duration_seconds: float, *, slow_ms: int) -> None:
    verb = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else "OTHER"
    if verb not in {"SELECT", "INSERT", "UPDATE", "DELETE", "WITH"}:
        verb = "OTHER"
    SQL_QUERIES.labels(verb).inc()
    SQL_SECONDS.labels(verb).observe(duration_seconds)
    _sql_count.set(_sql_count.get() + 1)
    _sql_seconds.set(_sql_seconds.get() + duration_seconds)
    if duration_seconds * 1000 >= slow_ms:
        logger.warning(
            "Slow SQL query",
            extra={
                "statement_kind": verb,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
        )


def observe_operation(
    *,
    component: str,
    operation: str,
    bot_code: str = "system",
    status: str,
    started: float,
    slow_ms: int,
    profile_enabled: bool,
) -> None:
    duration = time.perf_counter() - started
    OPERATION_SECONDS.labels(component, operation, bot_code, status).observe(duration)
    if duration * 1000 >= slow_ms:
        SLOW_OPERATIONS.labels(component, operation).inc()
        logger.warning(
            "Slow application operation",
            extra={
                "component": component,
                "operation": operation,
                "bot_code": bot_code,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
                "sql_queries": request_sql_stats()[0],
                "sql_duration_ms": round(request_sql_stats()[1] * 1000, 2),
            },
        )
    elif profile_enabled:
        logger.info(
            "Application operation profile",
            extra={
                "component": component,
                "operation": operation,
                "bot_code": bot_code,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
                "sql_queries": request_sql_stats()[0],
                "sql_duration_ms": round(request_sql_stats()[1] * 1000, 2),
            },
        )


def next_idle_delay(current: float, base: float, maximum: float) -> float:
    if current <= 0:
        return base
    return min(maximum, max(base, current * 1.7))
