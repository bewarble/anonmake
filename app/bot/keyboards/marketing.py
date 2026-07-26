from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Запустить",
                    callback_data="adminm:broadcast:confirm",
                ),
                InlineKeyboardButton(
                    text="✖️ Отмена",
                    callback_data="adminm:broadcast:cancel",
                ),
            ]
        ]
    )
