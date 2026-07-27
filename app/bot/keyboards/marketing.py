from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def broadcast_text_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✖️ Отмена",
                    callback_data="adminm:broadcast:cancel",
                )
            ]
        ]
    )


def broadcast_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Ответить",
                    callback_data="adminm:broadcast:preview",
                ),
                InlineKeyboardButton(
                    text="👤 Узнать кто это",
                    callback_data="adminm:broadcast:preview",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Запустить",
                    callback_data="adminm:broadcast:confirm",
                ),
                InlineKeyboardButton(
                    text="✖️ Отмена",
                    callback_data="adminm:broadcast:cancel",
                ),
            ],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return broadcast_preview_keyboard()
