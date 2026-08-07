from urllib.parse import quote

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup


SHARE_TEXT = "По этой ссылке можно мне прислать анонимное сообщение:\n👉 {link}"


def personal_link_share_keyboard(link: str) -> InlineKeyboardMarkup:
    full_link = link if link.startswith("https://") else f"https://{link}"
    short_link = full_link.removeprefix("https://")
    share_text = SHARE_TEXT.format(link=short_link)
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
                    url=(
                        "https://t.me/share/url/?"
                        f"url=&text={encoded_text}"
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
