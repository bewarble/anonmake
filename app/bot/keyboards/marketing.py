from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.ui import (
    ACTION_CANCEL,
    BROADCAST_START,
    QUESTION_ANSWER,
    QUESTION_REVEAL,
)


def broadcast_text_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data="adminm:broadcast:back_audience",
                )
            ],
            [
                InlineKeyboardButton(
                    text=ACTION_CANCEL,
                    callback_data="adminm:broadcast:cancel",
                )
            ],
        ]
    )


def broadcast_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=QUESTION_ANSWER,
                    callback_data="adminm:broadcast:preview",
                )
            ],
            [
                InlineKeyboardButton(
                    text=QUESTION_REVEAL,
                    callback_data="adminm:broadcast:preview",
                )
            ],
            [
                InlineKeyboardButton(
                    text=BROADCAST_START,
                    callback_data="adminm:broadcast:confirm",
                ),
                InlineKeyboardButton(
                    text=ACTION_CANCEL,
                    callback_data="adminm:broadcast:cancel",
                ),
            ],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return broadcast_preview_keyboard()
