from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.personal_link import personal_link_share_keyboard
from app.bot.ui import ACTION_CANCEL, QUESTION_ANSWER, QUESTION_REVEAL


def answer_question_keyboard(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=QUESTION_ANSWER,
                    callback_data=f"answer:{question_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=QUESTION_REVEAL,
                    callback_data=f"reveal:{question_id}",
                ),
            ],
        ]
    )


def answer_received_keyboard(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=QUESTION_ANSWER,
                    callback_data=f"answer_back:{question_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=QUESTION_REVEAL,
                    callback_data=f"reveal_answer:{question_id}",
                ),
            ],
        ]
    )


def write_more_keyboard(recipient_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Написать ещё",
                    callback_data=f"ask_again:{recipient_id}",
                )
            ]
        ]
    )


def answer_share_keyboard(link: str) -> InlineKeyboardMarkup:
    return personal_link_share_keyboard(link)


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ACTION_CANCEL, callback_data="cancel")]
        ]
    )
