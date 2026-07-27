from urllib.parse import urlencode

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def personal_link_share_keyboard(link: str) -> InlineKeyboardMarkup:
    query = urlencode(
        {
            "url": link,
            "text": "Напишите мне анонимное сообщение 💌",
        }
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Поделиться",
                    url=f"https://t.me/share/url?{query}",
                )
            ]
        ]
    )
