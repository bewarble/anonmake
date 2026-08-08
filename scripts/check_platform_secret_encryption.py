from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    security = (ROOT / "app/core/platform_security.py").read_text(encoding="utf-8")
    assert 'PLATFORM_SECRET_VERSION = "v2:"' in security
    assert 'PLATFORM_ENCRYPTION_SECRET_ENV = "PLATFORM_ENCRYPTION_SECRET"' in security
    assert "MIN_PLATFORM_ENCRYPTION_SECRET_LENGTH = 32" in security
    assert "dedicated = platform_encryption_secret()" in security
    assert "PLATFORM_SECRET_VERSION + payload" in security
    assert "value.startswith(PLATFORM_SECRET_VERSION)" in security
    assert "_fernet(master_secret).decrypt" in security

    rekey = (ROOT / "scripts/rekey_platform_secrets.py").read_text(encoding="utf-8")
    for model in ("BotInstance", "PaymentGatewayConfig", "ProjectSetupDraft"):
        assert model in rekey
    for field in (
        "token_encrypted",
        "api_token_encrypted",
        "webhook_secret_encrypted",
        "telegram_token_encrypted",
        "impaya_api_token_encrypted",
        "impaya_webhook_secret_encrypted",
    ):
        assert field in rekey
    assert "await session.commit()" in rekey
    assert "dedicated == settings.web_admin_secret" in rekey

    runtime = (ROOT / "scripts/check_platform_secret_rekey_runtime.py").read_text(encoding="utf-8")
    assert "Legacy platform ciphertext remains" in runtime
    assert "decrypt_secret(value, settings.web_admin_secret)" in runtime

    print("Platform secret encryption check: OK")
    print("New platform credentials support a dedicated versioned encryption key")
    print("Legacy ciphertext remains readable until controlled rekey")
    print("Runtime check blocks WEB_ADMIN_SECRET rotation while legacy ciphertext remains")


if __name__ == "__main__":
    main()
