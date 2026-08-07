from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot.ui import (
    ADMIN_BROADCAST,
    ADMIN_EXPORT,
    ADMIN_PROFIT,
    ADMIN_SOURCES,
    ADMIN_STATISTICS,
    USER_HELP,
    USER_PERSONAL_LINK,
)
from app.core.config import load_settings


def main_menu_keyboard(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    if is_admin:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=ADMIN_STATISTICS)],
                [
                    KeyboardButton(text=ADMIN_PROFIT),
                    KeyboardButton(text=ADMIN_BROADCAST),
                ],
                [
                    KeyboardButton(text=ADMIN_SOURCES),
                    KeyboardButton(text=ADMIN_EXPORT),
                ],
            ],
            resize_keyboard=True,
            input_field_placeholder="Выберите раздел",
        )

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=USER_PERSONAL_LINK)],
            [KeyboardButton(text=USER_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def main_menu_for(telegram_id: int | None) -> ReplyKeyboardMarkup:
    is_admin = (
        telegram_id is not None
        and telegram_id in load_settings().admin_ids_set
    )
    return main_menu_keyboard(is_admin=is_admin)
