from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import load_settings


def require_public_https(name: str, value: str) -> None:
    parsed = urlparse(value.strip())
    assert parsed.scheme == "https" and parsed.netloc, f"{name} must be a public https URL"
    host = (parsed.hostname or "").lower()
    assert host not in {"localhost", "127.0.0.1", "0.0.0.0"}, f"{name} points to localhost"


def reject_test_value(name: str, value: str) -> None:
    normalized = value.strip().lower()
    assert "stage" not in normalized and "test" not in normalized, (
        f"{name} still looks like staging/test configuration: {value}"
    )


def main() -> None:
    settings = load_settings()

    assert settings.billing_enabled, "BILLING_ENABLED must be true for public launch"
    assert settings.billing_automatic_charges_enabled, (
        "BILLING_AUTOMATIC_CHARGES_ENABLED must be true: public copy promises auto-renewal"
    )
    assert not settings.payment_test_commands_enabled, (
        "PAYMENT_TEST_COMMANDS_ENABLED must be false for public launch"
    )

    require_public_https("PUBLIC_BASE_URL", settings.public_base_url)
    if settings.offer_url.strip():
        require_public_https("OFFER_URL", settings.offer_url)

    assert settings.impaya_api_token.strip(), "IMPAYA_API_TOKEN is missing"
    assert settings.impaya_payment_form_url_template.strip(), (
        "IMPAYA_PAYMENT_FORM_URL_TEMPLATE is missing"
    )
    reject_test_value("IMPAYA_API_URL", settings.impaya_api_url)

    effective_binding_terminal = (
        settings.impaya_binding_terminal_name or settings.impaya_terminal_name
    )
    effective_recurrent_terminal = (
        settings.impaya_recurrent_terminal_name or settings.impaya_terminal_name
    )
    reject_test_value("Impaya binding terminal", effective_binding_terminal)
    reject_test_value("Impaya recurrent terminal", effective_recurrent_terminal)

    assert settings.trial_price_kopecks == 100
    assert settings.trial_duration_hours == 24
    assert settings.primary_price_kopecks == 29900
    assert settings.primary_duration_days == 3
    assert settings.fallback_price_kopecks == 9900
    assert settings.fallback_duration_days == 1

    identities = settings.configured_bot_identities()
    assert identities, "No configured Telegram bot identities"

    print("Bot public launch configuration: OK")
    print(f"Configured fixed bot identities: {len(identities)}")
    print("Billing and automatic renewal: enabled")
    print("Test payment commands: disabled")
    print("Public URLs: HTTPS")
    print("Impaya endpoint and terminals: non-test")
    print("Public billing copy matches runtime amounts and durations")


if __name__ == "__main__":
    main()
