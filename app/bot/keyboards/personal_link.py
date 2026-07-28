from urllib.parse import urlencode

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SHARE_TEXT = (
    "Есть вопрос, который давно хотелось мне задать? 👀\n\n"
    "Напиши анонимно — я не узнаю, кто отправил сообщение 💌"
)


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
                    text="Поделиться",
                    url=f"https://t.me/share/url?{query}",
                )
            ]
        ]
    )
