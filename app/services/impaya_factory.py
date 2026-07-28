from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.platform_security import decrypt_secret
from app.repositories.platform_admin import PlatformAdminRepository
from app.services.impaya import ImpayaClient


@dataclass(slots=True, frozen=True)
class ImpayaRuntimeConfig:
    api_url: str
    api_token: str
    auth_header: str
    auth_prefix: str
    protocol_version: str
    terminal_name: str
    binding_terminal_name: str
    recurrent_terminal_name: str
    payment_form_url_template: str
    webhook_secret: str


async def load_impaya_config(
    session: AsyncSession,
    settings: Settings,
    bot_id: int,
) -> ImpayaRuntimeConfig:
    item = await PlatformAdminRepository(session).gateway_for_bot(bot_id)
    if item is None:
        return ImpayaRuntimeConfig(
            api_url=settings.impaya_api_url,
            api_token=settings.impaya_api_token,
            auth_header=settings.impaya_auth_header,
            auth_prefix=settings.impaya_auth_prefix,
            protocol_version=settings.impaya_protocol_version,
            terminal_name=settings.impaya_terminal_name,
            binding_terminal_name=(
                settings.impaya_binding_terminal_name
                or settings.impaya_terminal_name
            ),
            recurrent_terminal_name=(
                settings.impaya_recurrent_terminal_name
                or settings.impaya_terminal_name
            ),
            payment_form_url_template=settings.impaya_payment_form_url_template,
            webhook_secret=settings.impaya_webhook_secret,
        )

    secret = settings.web_admin_secret
    return ImpayaRuntimeConfig(
        api_url=item.api_url,
        api_token=decrypt_secret(item.api_token_encrypted, secret),
        auth_header=item.auth_header,
        auth_prefix=item.auth_prefix,
        protocol_version=item.protocol_version,
        terminal_name=item.terminal_name,
        binding_terminal_name=item.binding_terminal_name,
        recurrent_terminal_name=item.recurrent_terminal_name,
        payment_form_url_template=item.payment_form_url_template,
        webhook_secret=decrypt_secret(item.webhook_secret_encrypted, secret),
    )


def create_impaya_client(config: ImpayaRuntimeConfig) -> ImpayaClient:
    return ImpayaClient(
        config.api_url,
        config.api_token,
        config.binding_terminal_name or config.terminal_name,
        auth_header=config.auth_header,
        auth_prefix=config.auth_prefix,
        protocol_version=config.protocol_version,
        recurrent_terminal_name=(
            config.recurrent_terminal_name or config.terminal_name
        ),
    )
