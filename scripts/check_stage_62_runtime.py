from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError
from sqlalchemy import select

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.services.bot_credentials import resolve_bot_token

EXPECTED_COMMANDS = ["start", "cancel"]


async def check_telegram_commands() -> None:
    settings = load_settings()
    async with SessionFactory() as session:
        instances = list(
            (
                await session.execute(
                    select(BotInstance)
                    .where(BotInstance.is_active.is_(True))
                    .order_by(BotInstance.id)
                )
            ).scalars()
        )

        assert instances, "No active bot instances found"
        checked = 0
        for instance in instances:
            print(
                f"Stage 62 runtime: checking {instance.code} / @{instance.username.lstrip('@')}"
            )
            token = await resolve_bot_token(session, settings, instance)
            bot = Bot(token=token)
            try:
                try:
                    me = await bot.get_me()
                    commands = await bot.get_my_commands()
                except TelegramUnauthorizedError as exc:
                    raise AssertionError(
                        f"Telegram token is unauthorized for {instance.code} / "
                        f"@{instance.username.lstrip('@')}"
                    ) from exc
            finally:
                await bot.session.close()

            actual = [item.command for item in commands]
            assert actual == EXPECTED_COMMANDS, (
                f"@{instance.username} public commands mismatch: "
                f"expected={EXPECTED_COMMANDS}, actual={actual}"
            )
            assert (me.username or "").lower() == instance.username.lstrip("@").lower(), (
                f"bot username mismatch for {instance.code}: "
                f"database={instance.username}, telegram={me.username}"
            )
            checked += 1
            print(
                f"Stage 62 runtime: @{me.username} commands OK: /start, /cancel"
            )

    print(f"Stage 62 runtime: active bots checked: {checked}")


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
        print(
            "Stage 62 runtime: billing disabled "
            "(allowed for runtime smoke; launch-check is stricter)"
        )


async def main_async() -> None:
    check_runtime_config()
    await check_telegram_commands()
    print("Stage 62 runtime check: OK")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
