from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    if is_admin:
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📊 Статистика"),
                    KeyboardButton(text="👥 Пользователи"),
                ],
                [
                    KeyboardButton(text="📣 Источники"),
                    KeyboardButton(text="📢 Рассылки"),
                ],
                [
                    KeyboardButton(text="💳 Финансы"),
                    KeyboardButton(text="📨 Доставка"),
                ],
                [
                    KeyboardButton(text="🔗 Моя ссылка"),
                    KeyboardButton(text="✨ Как это работает"),
                ],
            ],
            resize_keyboard=True,
            input_field_placeholder="Управление проектом",
        )

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔗 Моя ссылка")],
            [KeyboardButton(text="✨ Как это работает")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
