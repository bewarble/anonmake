from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CurrentBot:
    id: int
    code: str
    username: str
    display_name: str


_current_bot: ContextVar[CurrentBot | None] = ContextVar(
    "anonmake_current_bot",
    default=None,
)


def set_current_bot(bot: CurrentBot) -> Token[CurrentBot | None]:
    return _current_bot.set(bot)


def reset_current_bot(token: Token[CurrentBot | None]) -> None:
    _current_bot.reset(token)


def get_current_bot() -> CurrentBot | None:
    return _current_bot.get()


def require_current_bot() -> CurrentBot:
    bot = get_current_bot()
    if bot is None:
        raise RuntimeError("Current bot context is not initialized")
    return bot
