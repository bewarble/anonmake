from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    if is_admin:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Статистика")],
                [
                    KeyboardButton(text="Рассылка"),
                    KeyboardButton(text="Прибыль"),
                ],
                [
                    KeyboardButton(text="Выгрузка"),
                    KeyboardButton(text="Рефералы"),
                ],
            ],
            resize_keyboard=True,
            input_field_placeholder="Админ-панель",
        )

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔗 Моя ссылка")],
            [KeyboardButton(text="✨ Как это работает")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
