from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import load_settings
from app.core.platform_security import (
    PLATFORM_SECRET_VERSION,
    decrypt_secret,
    encrypt_secret,
    platform_encryption_secret,
    validate_platform_encryption_secret,
)
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.models.platform_admin import PaymentGatewayConfig
from app.models.project_setup import ProjectSetupDraft


async def _rekey_value(value: str | None, legacy_secret: str) -> tuple[str | None, bool]:
    if not value or value.startswith(PLATFORM_SECRET_VERSION):
        if value:
            decrypt_secret(value, legacy_secret)
        return value, False
    plaintext = decrypt_secret(value, legacy_secret)
    converted = encrypt_secret(plaintext, legacy_secret)
    if not converted.startswith(PLATFORM_SECRET_VERSION):
        raise RuntimeError("Dedicated platform encryption key was not used")
    if decrypt_secret(converted, legacy_secret) != plaintext:
        raise RuntimeError("Rekey verification failed")
    return converted, True


async def main_async() -> None:
    settings = load_settings()
    dedicated = platform_encryption_secret()
    if not dedicated:
        raise RuntimeError("PLATFORM_ENCRYPTION_SECRET is not configured")
    validate_platform_encryption_secret(dedicated)
    if dedicated == settings.web_admin_secret:
        raise RuntimeError(
            "PLATFORM_ENCRYPTION_SECRET must differ from WEB_ADMIN_SECRET"
        )

    changed = 0
    checked = 0
    async with SessionFactory() as session:
        bots = list((await session.scalars(select(BotInstance))).all())
        gateways = list((await session.scalars(select(PaymentGatewayConfig))).all())
        drafts = list((await session.scalars(select(ProjectSetupDraft))).all())

        for bot in bots:
            checked += bool(bot.token_encrypted)
            bot.token_encrypted, converted = await _rekey_value(
                bot.token_encrypted, settings.web_admin_secret
            )
            changed += int(converted)

        for gateway in gateways:
            for field in ("api_token_encrypted", "webhook_secret_encrypted"):
                value = getattr(gateway, field)
                checked += bool(value)
                converted_value, converted = await _rekey_value(
                    value, settings.web_admin_secret
                )
                setattr(gateway, field, converted_value)
                changed += int(converted)

        for draft in drafts:
            for field in (
                "telegram_token_encrypted",
                "impaya_api_token_encrypted",
                "impaya_webhook_secret_encrypted",
            ):
                value = getattr(draft, field)
                checked += bool(value)
                converted_value, converted = await _rekey_value(
                    value, settings.web_admin_secret
                )
                setattr(draft, field, converted_value)
                changed += int(converted)

        # One transaction: either every known platform credential is converted
        # and verified, or none of them is persisted.
        await session.flush()

        for bot in bots:
            if bot.token_encrypted:
                assert bot.token_encrypted.startswith(PLATFORM_SECRET_VERSION)
                decrypt_secret(bot.token_encrypted, settings.web_admin_secret)
        for gateway in gateways:
            for value in (gateway.api_token_encrypted, gateway.webhook_secret_encrypted):
                if value:
                    assert value.startswith(PLATFORM_SECRET_VERSION)
                    decrypt_secret(value, settings.web_admin_secret)
        for draft in drafts:
            for value in (
                draft.telegram_token_encrypted,
                draft.impaya_api_token_encrypted,
                draft.impaya_webhook_secret_encrypted,
            ):
                if value:
                    assert value.startswith(PLATFORM_SECRET_VERSION)
                    decrypt_secret(value, settings.web_admin_secret)

        await session.commit()

    print("Platform secret rekey: OK")
    print(f"Credentials checked: {checked}")
    print(f"Credentials converted to v2: {changed}")
    print("WEB_ADMIN_SECRET can be rotated only after a runtime rekey check passes.")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
