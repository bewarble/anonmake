from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def cancel_source_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✖️ Отменить",
                    callback_data="source:create:cancel",
                )
            ]
        ]
    )


def source_delete_confirm_keyboard(source_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить",
                    callback_data=f"source:delete_confirm:{source_id}",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="admin25:referrals",
                ),
            ]
        ]
    )
