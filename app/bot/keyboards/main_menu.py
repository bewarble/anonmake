from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔗 Моя ссылка"),
                KeyboardButton(text="📥 Мои вопросы"),
            ],
            [
                KeyboardButton(text="⭐ Подписка"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
