from urllib.parse import quote

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup


SHARE_TEXT = "Отправь мне анонимное сообщение 👉 {link}"


def personal_link_share_keyboard(link: str) -> InlineKeyboardMarkup:
    short_link = link.removeprefix("https://")
    share_text = SHARE_TEXT.format(link=short_link)
    encoded_text = quote(share_text, safe="")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Поделиться ссылкой",
                    url=(
                        "https://t.me/share/url/?"
                        f"url=%20&text={encoded_text}"
                    ),
                )
            ]
        ]
    )


def personal_link_copy_keyboard(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Скопировать ссылку",
                    copy_text=CopyTextButton(text=link),
                )
            ]
        ]
    )
