from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def delivery_dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Последние ошибки",
                    callback_data="admin:delivery:failed",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="admin:delivery",
                ),
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data="admin:home",
                ),
            ],
        ]
    )


def failed_deliveries_keyboard(ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"Повторить #{delivery_id}",
                callback_data=f"admin:delivery:retry:{delivery_id}",
            )
        ]
        for delivery_id in ids
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="← К очереди",
                callback_data="admin:delivery",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
