from __future__ import annotations

from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage


def build_fsm_storage(redis_url: str) -> RedisStorage:
    """Build restart-safe FSM storage isolated by Telegram bot id."""
    return RedisStorage.from_url(
        redis_url,
        key_builder=DefaultKeyBuilder(with_bot_id=True),
    )
