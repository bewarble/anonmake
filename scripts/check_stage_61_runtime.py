from __future__ import annotations

import asyncio

from aiogram.fsm.storage.base import StorageKey

from app.bot.storage import build_fsm_storage
from app.core.config import load_settings


async def check() -> None:
    settings = load_settings()
    storage = build_fsm_storage(settings.redis_url)
    key = StorageKey(
        bot_id=9_999_961,
        chat_id=9_999_961,
        user_id=9_999_961,
    )
    try:
        await storage.set_state(key, "stage61:runtime")
        await storage.set_data(key, {"probe": "ok"})
        assert await storage.get_state(key) == "stage61:runtime"
        assert await storage.get_data(key) == {"probe": "ok"}
        await storage.set_state(key, None)
        await storage.set_data(key, {})
    finally:
        await storage.close()


def main() -> None:
    asyncio.run(check())
    print("Stage 61 runtime: Redis FSM read/write/delete OK")
    print("Stage 61 runtime check: OK")


if __name__ == "__main__":
    main()
