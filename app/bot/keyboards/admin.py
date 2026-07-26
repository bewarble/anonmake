from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛠 Центр управления",
                    callback_data="adminx:home",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Пользователи",
                    callback_data="adminx:users:recent:0",
                ),
                InlineKeyboardButton(
                    text="👑 Подписки",
                    callback_data="adminx:subs:active:0",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💳 Платежи",
                    callback_data="adminx:payments:all:0",
                ),
                InlineKeyboardButton(
                    text="📨 Доставка",
                    callback_data="admin:delivery",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📈 Аналитика",
                    callback_data="admin:analytics",
                ),
                InlineKeyboardButton(
                    text="⚙️ Система",
                    callback_data="admin:system",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📣 Источники",
                    callback_data="adminm:sources",
                ),
                InlineKeyboardButton(
                    text="📢 Рассылки",
                    callback_data="adminm:broadcasts",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔎 Найти",
                    callback_data="admin:find",
                ),
                InlineKeyboardButton(
                    text="🧾 Журнал",
                    callback_data="admin:audit",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="admin:home",
                )
            ],
        ]
    )


def user_actions(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="VIP +1 день",
                    callback_data=f"admin:vip:{user_id}:1",
                ),
                InlineKeyboardButton(
                    text="VIP +7 дней",
                    callback_data=f"admin:vip:{user_id}:7",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="VIP +30 дней",
                    callback_data=f"admin:vip:{user_id}:30",
                ),
                InlineKeyboardButton(
                    text="Снять VIP",
                    callback_data=f"admin:vip_revoke:{user_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="← В админ-панель",
                    callback_data="adminx:home",
                )
            ],
        ]
    )


def back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data="adminx:home",
                )
            ]
        ]
    )
