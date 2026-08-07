from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SHARE_TEXT = "Отправь мне анонимное сообщение 👉"


def personal_link_share_keyboard(link: str) -> InlineKeyboardMarkup:
    encoded_url = quote(link, safe="")
    encoded_text = quote(SHARE_TEXT, safe="")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Поделиться ссылкой",
                    url=(
                        "tg://msg_url?"
                        f"url={encoded_url}&text={encoded_text}"
                    ),
                )
            ]
        ]
    )
