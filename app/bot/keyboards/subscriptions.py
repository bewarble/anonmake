from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def cancel_subscription_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отключить",
                    callback_data="subscription:cancel:confirm",
                ),
                InlineKeyboardButton(
                    text="Оставить",
                    callback_data="subscription:cancel:keep",
                ),
            ]
        ]
    )
