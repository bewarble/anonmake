from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def admin_reply_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Статистика")],
            [
                KeyboardButton(text="Рассылка"),
                KeyboardButton(text="Прибыль"),
            ],
            [
                KeyboardButton(text="Выгрузка"),
                KeyboardButton(text="Источники"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Админ-панель",
    )
