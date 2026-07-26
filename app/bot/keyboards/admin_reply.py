from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def broadcast_kind_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📰 Новостная",
                    callback_data="adminm:broadcast:kind:news",
                ),
                InlineKeyboardButton(
                    text="⭐ Premium",
                    callback_data="adminm:broadcast:kind:subscription",
                ),
            ]
        ]
    )


def referral_sources_keyboard(sources) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"📣 {source.name}",
                callback_data=f"adminm:source:{source.id}",
            )
        ]
        for source in sources
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="➕ Создать ссылку",
                callback_data="adminm:source:create",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
