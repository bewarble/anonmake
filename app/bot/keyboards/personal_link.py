from urllib.parse import quote

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup


SHARE_TEXT = "Отправь мне анонимное сообщение 👇"


def personal_link_share_keyboard(link: str) -> InlineKeyboardMarkup:
    full_link = link if link.startswith("https://") else f"https://{link}"
    encoded_link = quote(full_link, safe="")
    encoded_text = quote(SHARE_TEXT, safe="")
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
                    url=(
                        "https://t.me/share/url/?"
                        f"url={encoded_link}&text={encoded_text}"
                    ),
                )
            ],
        ]
    )


def personal_link_copy_keyboard(link: str) -> InlineKeyboardMarkup:
    full_link = link if link.startswith("https://") else f"https://{link}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Скопировать ссылку",
                    copy_text=CopyTextButton(text=full_link),
                )
            ]
        ]
    )
