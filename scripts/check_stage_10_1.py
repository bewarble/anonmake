from app.core.config import load_settings
from app.services.impaya import ImpayaClient


def check() -> None:
    settings = load_settings()

    assert settings.impaya_protocol_version == "v2.0"
    assert settings.impaya_auth_prefix == "Bearer "

    client = ImpayaClient(
        settings.impaya_api_url,
        "test-token",
        settings.impaya_terminal_name,
        auth_header=settings.impaya_auth_header,
        auth_prefix=settings.impaya_auth_prefix,
        protocol_version=settings.impaya_protocol_version,
    )

    headers = client._client.headers

    assert headers.get("protocol") == "v2.0"
    assert headers.get("content-type") == "application/json"
    assert headers.get("authorization") == "Bearer test-token"

    print("Stage 10.1 check: OK")
    print("Impaya headers:")
    print("  protocol: v2.0")
    print("  Content-Type: application/json")
    print("  Authorization: Bearer <token>")


if __name__ == "__main__":
    check()
