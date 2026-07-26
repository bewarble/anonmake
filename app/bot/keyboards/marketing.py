from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def sources_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Создать источник",
                    callback_data="adminm:source:create",
                )
            ],
            [
                InlineKeyboardButton(
                    text="← В панель",
                    callback_data="adminx:home",
                )
            ],
        ]
    )


def source_list_keyboard(sources) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"📣 {source.name}",
                callback_data=f"adminm:source:{source.id}",
            )
        ]
        for source in sources
    ]
    rows.extend(sources_menu().inline_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def broadcasts_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📰 Новостная",
                    callback_data="adminm:broadcast:kind:news",
                ),
                InlineKeyboardButton(
                    text="⭐ Подписка",
                    callback_data="adminm:broadcast:kind:subscription",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="← В панель",
                    callback_data="adminx:home",
                )
            ],
        ]
    )


def audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Все",
                    callback_data="adminm:broadcast:audience:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Без VIP",
                    callback_data="adminm:broadcast:audience:non_vip",
                ),
                InlineKeyboardButton(
                    text="С VIP",
                    callback_data="adminm:broadcast:audience:vip",
                ),
            ],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Запустить",
                    callback_data="adminm:broadcast:confirm",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="adminm:broadcast:cancel",
                ),
            ]
        ]
    )
