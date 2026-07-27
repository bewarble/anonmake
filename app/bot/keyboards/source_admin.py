from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.ui import ACTION_CANCEL, SOURCE_DELETE_CONFIRM


def cancel_source_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=ACTION_CANCEL,
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
                    text=SOURCE_DELETE_CONFIRM,
                    callback_data=f"source:delete_confirm:{source_id}",
                ),
                InlineKeyboardButton(
                    text=ACTION_CANCEL,
                    callback_data="admin25:referrals",
                ),
            ]
        ]
    )
