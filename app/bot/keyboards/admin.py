from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin:stats",
                ),
                InlineKeyboardButton(
                    text="💳 Платежи",
                    callback_data="admin:payments",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📈 Аналитика",
                    callback_data="admin:analytics",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔎 Найти пользователя",
                    callback_data="admin:find",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📨 Доставка",
                    callback_data="admin:delivery",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 Журнал",
                    callback_data="admin:audit",
                ),
                InlineKeyboardButton(
                    text="⚙️ Система",
                    callback_data="admin:system",
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
                    callback_data="admin:home",
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
                    callback_data="admin:home",
                )
            ]
        ]
    )
