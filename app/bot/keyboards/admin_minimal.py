from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Пользователи", callback_data="adm:users"),
                InlineKeyboardButton(text="📈 Рост", callback_data="adm:growth"),
            ],
            [
                InlineKeyboardButton(text="💳 Финансы", callback_data="adm:finance"),
                InlineKeyboardButton(text="⚙️ Система", callback_data="adm:operations"),
            ],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="adm:home")],
        ]
    )


def users_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Список", callback_data="adminx:users:recent:0"),
                InlineKeyboardButton(text="🔎 Поиск", callback_data="admin:find"),
            ],
            [
                InlineKeyboardButton(text="⭐ Premium", callback_data="adminx:subs:active:0"),
                InlineKeyboardButton(text="🗂 CRM", callback_data="adminx:users:recent:0"),
            ],
            [InlineKeyboardButton(text="← Назад", callback_data="adm:home")],
        ]
    )


def growth_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Аналитика", callback_data="admin:analytics"),
                InlineKeyboardButton(text="📣 Источники", callback_data="adminm:sources"),
            ],
            [InlineKeyboardButton(text="📢 Рассылки", callback_data="adminm:broadcasts")],
            [InlineKeyboardButton(text="← Назад", callback_data="adm:home")],
        ]
    )


def finance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Платежи", callback_data="adminx:payments:all:0"),
                InlineKeyboardButton(text="⭐ Подписки", callback_data="adminx:subs:active:0"),
            ],
            [InlineKeyboardButton(text="📈 Аналитика", callback_data="admin:analytics")],
            [InlineKeyboardButton(text="← Назад", callback_data="adm:home")],
        ]
    )


def operations_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📨 Доставка", callback_data="admin:delivery"),
                InlineKeyboardButton(text="⚙️ Сервисы", callback_data="admin:system"),
            ],
            [InlineKeyboardButton(text="🧾 Журнал", callback_data="admin:audit")],
            [InlineKeyboardButton(text="← Назад", callback_data="adm:home")],
        ]
    )
