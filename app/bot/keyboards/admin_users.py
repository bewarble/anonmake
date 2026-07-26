from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def users_list_keyboard(
    users,
    *,
    page: int,
    has_next: bool,
) -> InlineKeyboardMarkup:
    rows = []

    for user in users:
        username = f"@{user.username}" if user.username else "без username"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {user.id} · {username}",
                    callback_data=f"admin:user:{user.id}",
                )
            ]
        )

    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="←",
                callback_data=f"admin:users:{page - 1}",
            )
        )
    if has_next:
        navigation.append(
            InlineKeyboardButton(
                text="→",
                callback_data=f"admin:users:{page + 1}",
            )
        )
    if navigation:
        rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(
                text="🔎 Найти",
                callback_data="admin:find",
            ),
            InlineKeyboardButton(
                text="← Назад",
                callback_data="admin:home",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_card_keyboard(user_id: int) -> InlineKeyboardMarkup:
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
                    text="← Пользователи",
                    callback_data="admin:users:0",
                )
            ],
        ]
    )
