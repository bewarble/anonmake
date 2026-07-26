from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def reveal_checkout_keyboard(
    *,
    payment_url: str,
    offer_url: str,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="👑 Получить VIP за 1 ₽",
                url=payment_url,
            )
        ],
    ]
    if offer_url:
        rows.append(
            [InlineKeyboardButton(text="📄 Оферта", url=offer_url)]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
