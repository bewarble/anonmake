from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def broadcast_audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Всем",
                    callback_data="admin25:broadcast:audience:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ С VIP",
                    callback_data="admin25:broadcast:audience:vip",
                ),
                InlineKeyboardButton(
                    text="Без VIP",
                    callback_data="admin25:broadcast:audience:non_vip",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✖️ Отмена",
                    callback_data="admin25:broadcast:cancel",
                )
            ],
        ]
    )


def referrals_keyboard(sources) -> InlineKeyboardMarkup:
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


def referral_card_keyboard(source_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="← К списку",
                    callback_data="admin25:referrals",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"source:delete:{source_id}",
                )
            ],
        ]
    )
