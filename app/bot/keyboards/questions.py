from urllib.parse import quote

from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

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
    full_link = link if link.startswith("https://") else f"https://{link}"
    short_link = full_link.removeprefix("https://")
    share_text = f"Отправь мне анонимное сообщение 👉 {short_link}"
    encoded_text = quote(share_text, safe="")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Скопировать ссылку",
                    copy_text=CopyTextButton(text=full_link),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📤 Выложить в каналы / чаты",
                    url=f"https://t.me/share/url/?url=%20&text={encoded_text}",
                )
            ],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ACTION_CANCEL, callback_data="cancel")]
        ]
    )
