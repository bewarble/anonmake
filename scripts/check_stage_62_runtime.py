from __future__ import annotations

import asyncio

from aiogram import Bot

from app.core.config import load_settings

EXPECTED_COMMANDS = ["start", "cancel"]


async def check_telegram_commands() -> None:
    settings = load_settings()
    bot = Bot(token=settings.require_bot_token())
    try:
        me = await bot.get_me()
        commands = await bot.get_my_commands()
    finally:
        await bot.session.close()

    actual = [item.command for item in commands]
    assert actual == EXPECTED_COMMANDS, (
        f"public Telegram commands mismatch: expected={EXPECTED_COMMANDS}, actual={actual}"
    )

    configured_username = settings.bot_username.strip().lstrip("@").lower()
    if configured_username:
        assert (me.username or "").lower() == configured_username, (
            f"BOT_USERNAME mismatch: configured={configured_username}, telegram={me.username}"
        )
    print(f"Stage 62 runtime: @{me.username} commands OK: /start, /cancel")


def check_runtime_config() -> None:
    settings = load_settings()
    assert not settings.payment_test_commands_enabled, (
        "PAYMENT_TEST_COMMANDS_ENABLED must be false in launch runtime"
    )

    if settings.billing_enabled:
        assert settings.impaya_api_token.strip(), "IMPAYA_API_TOKEN is missing"
        assert settings.impaya_payment_form_url_template.strip(), (
            "IMPAYA_PAYMENT_FORM_URL_TEMPLATE is missing"
        )
        assert settings.public_base_url.strip().startswith("https://"), (
            "PUBLIC_BASE_URL must use https when billing is enabled"
        )
        assert settings.trial_price_kopecks == 100, (
            "TRIAL_PRICE_KOPECKS must match public copy: 1 ₽"
        )
        assert settings.trial_duration_hours == 24, (
            "TRIAL_DURATION_HOURS must match public copy: 1 day"
        )
        assert settings.primary_price_kopecks == 29900
        assert settings.primary_duration_days == 3
        assert settings.fallback_price_kopecks == 9900
        assert settings.fallback_duration_days == 1
        print("Stage 62 runtime: billing copy/config contract OK")
    else:
        print("Stage 62 runtime: billing disabled (allowed for runtime smoke; launch-check is stricter)")


async def main_async() -> None:
    check_runtime_config()
    await check_telegram_commands()
    print("Stage 62 runtime check: OK")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
