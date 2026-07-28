# Stage 39 — Performance, monitoring and stability

This consolidated stage adds lightweight Prometheus metrics, slow SQL and
operation diagnostics, adaptive worker backoff, a cached bot identity in the
Telegram database middleware, multibot workload indexes and an authenticated
admin performance page.

Detailed per-operation log messages are disabled by default. Slow operations
are still reported using the configured thresholds.

## Environment

- `PERFORMANCE_ENABLED=true`
- `PERF_PROFILE_ENABLED=false`
- `PERF_SLOW_OPERATION_MS=500`
- `PERF_SLOW_SQL_MS=150`
- `WORKER_IDLE_MAX_SECONDS=10`

## Admin

Open `/admin/performance` for a lightweight runtime snapshot. Prometheus data
remains available at `/metrics`.
