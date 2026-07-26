from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def export_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Все пользователи",
                    callback_data="admin25:export:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Только живые",
                    callback_data="admin25:export:alive",
                )
            ],
        ]
    )


def referral_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="← К списку",
                    callback_data="adminm:sources",
                )
            ]
        ]
    )


def broadcast_audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Всем",
                    callback_data="adminm:broadcast:audience:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ С Premium",
                    callback_data="adminm:broadcast:audience:vip",
                ),
                InlineKeyboardButton(
                    text="Без Premium",
                    callback_data="adminm:broadcast:audience:non_vip",
                ),
            ],
        ]
    )
