from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.ui import REVEAL_CLOSE, REVEAL_CONFIRM


def reveal_consent_keyboard(
    *,
    question_id: int,
    context: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=REVEAL_CONFIRM,
                    callback_data=f"reveal_confirm:{context}:{question_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=REVEAL_CLOSE,
                    callback_data="reveal_close",
                ),
            ],
        ]
    )


def reveal_checkout_keyboard(*, payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Перейти к оплате",
                    url=payment_url,
                )
            ]
        ]
    )
