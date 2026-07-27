from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def test_payment_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатить 1 ₽",
                    url=payment_url,
                )
            ]
        ]
    )
