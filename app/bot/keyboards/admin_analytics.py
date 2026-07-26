from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def analytics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="admin:analytics",
                ),
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data="admin:home",
                ),
            ]
        ]
    )
