from urllib.parse import urlencode

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SHARE_TEXT = "Отправь мне анонимное сообщение 👉"


def personal_link_share_keyboard(link: str) -> InlineKeyboardMarkup:
    query = urlencode(
        {
            "url": link,
            "text": SHARE_TEXT,
        }
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Поделиться ссылкой",
                    url=f"https://t.me/share/url?{query}",
                )
            ]
        ]
    )
