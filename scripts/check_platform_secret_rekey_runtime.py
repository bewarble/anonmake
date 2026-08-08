from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import load_settings
from app.core.platform_security import (
    PLATFORM_SECRET_VERSION,
    decrypt_secret,
    platform_encryption_secret,
    validate_platform_encryption_secret,
)
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.models.platform_admin import PaymentGatewayConfig
from app.models.project_setup import ProjectSetupDraft


async def main_async() -> None:
    dedicated = platform_encryption_secret()
    if not dedicated:
        print("Platform secret rekey runtime: dedicated key not configured; legacy mode")
        return
    validate_platform_encryption_secret(dedicated)

    settings = load_settings()
    if dedicated == settings.web_admin_secret:
        raise AssertionError(
            "PLATFORM_ENCRYPTION_SECRET must differ from WEB_ADMIN_SECRET"
        )

    values: list[tuple[str, str]] = []
    async with SessionFactory() as session:
        for bot in (await session.scalars(select(BotInstance))).all():
            if bot.token_encrypted:
                values.append((f"bot:{bot.id}:telegram", bot.token_encrypted))
        for gateway in (await session.scalars(select(PaymentGatewayConfig))).all():
            if gateway.api_token_encrypted:
                values.append((f"gateway:{gateway.id}:api", gateway.api_token_encrypted))
            if gateway.webhook_secret_encrypted:
                values.append((f"gateway:{gateway.id}:webhook", gateway.webhook_secret_encrypted))
        for draft in (await session.scalars(select(ProjectSetupDraft))).all():
            for field in (
                "telegram_token_encrypted",
                "impaya_api_token_encrypted",
                "impaya_webhook_secret_encrypted",
            ):
                value = getattr(draft, field)
                if value:
                    values.append((f"draft:{draft.id}:{field}", value))

    legacy = [name for name, value in values if not value.startswith(PLATFORM_SECRET_VERSION)]
    if legacy:
        preview = ", ".join(legacy[:10])
        raise AssertionError(
            "Legacy platform ciphertext remains after dedicated encryption key was configured: "
            + preview
        )

    for name, value in values:
        try:
            decrypt_secret(value, settings.web_admin_secret)
        except Exception as exc:
            raise AssertionError(f"Cannot decrypt {name}") from exc

    print("Platform secret rekey runtime: OK")
    print(f"v2 credentials verified: {len(values)}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
