from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def answer_question_keyboard(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Ответить",
                    callback_data=f"answer:{question_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Узнать кто это",
                    callback_data=f"reveal:{question_id}",
                )
            ],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
        ]
    )
