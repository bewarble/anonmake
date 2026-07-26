from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup


def serialize_markup(
    markup: InlineKeyboardMarkup | None,
) -> dict | None:
    if markup is None:
        return None
    return markup.model_dump(mode="json", exclude_none=True)


def deserialize_markup(
    value: dict | None,
) -> InlineKeyboardMarkup | None:
    if value is None:
        return None
    return InlineKeyboardMarkup.model_validate(value)
