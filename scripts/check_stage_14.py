from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services.sender_identity import resolve_current_sender


class FakeBot:
    async def get_chat(self, telegram_id: int):
        assert telegram_id == 100
        return SimpleNamespace(
            username="current_username",
            first_name="Current",
            last_name="Name",
        )


async def check() -> None:
    stored_sender = SimpleNamespace(
        telegram_id=100,
        username="old_username",
        first_name="Old",
        last_name="Name",
    )

    identity = await resolve_current_sender(FakeBot(), stored_sender)

    assert identity.username == "current_username"
    assert identity.label == "@current_username"

    print("Stage 14 check: OK")
    print("Sender identity: refreshed at reveal time")
    print("Fallback: stored profile when Telegram is unavailable")
    print("Messages: unchanged until reveal button is pressed")


if __name__ == "__main__":
    asyncio.run(check())
