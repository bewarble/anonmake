from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "app/web/security_headers.py").read_text(encoding="utf-8")
    assert '"X-Content-Type-Options", "nosniff"' in source
    assert '"X-Frame-Options", "DENY"' in source
    assert '"Referrer-Policy", "no-referrer"' in source
    assert '"Permissions-Policy"' in source
    assert 'request.url.path.startswith("/admin")' in source
    assert '"Cache-Control", "no-store"' in source
    assert "frame-ancestors 'none'" in source
    assert 'request.url.scheme == "https"' in source
    assert '"Strict-Transport-Security"' in source

    system = (ROOT / "app/web/admin_system.py").read_text(encoding="utf-8")
    assert "from app.web.security_headers import install_security_headers" in system
    assert "install_security_headers(web_app)" in system

    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert '"--proxy-headers"' in compose
    assert "FORWARDED_ALLOW_IPS" in compose
    assert '"--forwarded-allow-ips=*"' not in compose
    assert "127.0.0.1,172.16.0.0/12" in compose

    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "FORWARDED_ALLOW_IPS=" in example

    print("Web security headers check: OK")
    print("Admin responses are non-cacheable and protected from framing")
    print("HTTPS responses advertise HSTS")
    print("Forwarded headers are not trusted from arbitrary peers")


if __name__ == "__main__":
    main()
