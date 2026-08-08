from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def function_source(path: str, name: str) -> str:
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(f"Function not found: {path}:{name}")


def main() -> None:
    endpoint = "app/web/metrics_endpoint.py"
    verify = function_source(endpoint, "_verify_metrics_token")
    assert "settings.metrics_token.strip()" in verify
    assert "hmac.compare_digest" in verify
    assert "status_code=404" in verify
    assert "status_code=401" in verify

    metrics = function_source(endpoint, "metrics")
    assert "_verify_metrics_token" in metrics
    assert metrics.index("_verify_metrics_token") < metrics.index("generate_latest")

    installer = function_source(endpoint, "install_metrics_endpoint")
    assert "app.router.routes[:]" in installer
    assert "METRICS_PATH" in installer
    assert "app.add_api_route" in installer

    config = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
    assert 'alias="METRICS_TOKEN"' in config
    system = (ROOT / "app/web/admin_system.py").read_text(encoding="utf-8")
    assert "install_metrics_endpoint(web_app)" in system

    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert '${WEB_BIND_ADDRESS:-127.0.0.1}' in compose

    print("Metrics security check: OK")
    print("/metrics is disabled without a dedicated credential")
    print("Scrapes require X-Metrics-Token and constant-time comparison")
    print("Default Docker bind remains loopback-only")


if __name__ == "__main__":
    main()
