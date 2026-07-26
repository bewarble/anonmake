from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def control_center_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
                    text="🧾 Журнал",
                    callback_data="admin:audit",
                ),
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="adminx:home",
                ),
            ],
        ]
    )


def users_filters_keyboard(
    users,
    *,
    filter_name: str,
    page: int,
    has_next: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="Новые",
                callback_data="adminx:users:recent:0",
            ),
            InlineKeyboardButton(
                text="VIP",
                callback_data="adminx:users:vip:0",
            ),
            InlineKeyboardButton(
                text="Платившие",
                callback_data="adminx:users:paid:0",
            ),
        ]
    ]

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

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="←",
                callback_data=f"adminx:users:{filter_name}:{page - 1}",
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="→",
                callback_data=f"adminx:users:{filter_name}:{page + 1}",
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                text="🔎 Поиск",
                callback_data="admin:find",
            ),
            InlineKeyboardButton(
                text="← В панель",
                callback_data="adminx:home",
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payments_keyboard(
    rows_data,
    *,
    filter_name: str,
    page: int,
    has_next: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="Все",
                callback_data="adminx:payments:all:0",
            ),
            InlineKeyboardButton(
                text="✅",
                callback_data="adminx:payments:success:0",
            ),
            InlineKeyboardButton(
                text="❌",
                callback_data="adminx:payments:failed:0",
            ),
            InlineKeyboardButton(
                text="⏳",
                callback_data="adminx:payments:pending:0",
            ),
        ]
    ]

    for row in rows_data:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"#{row.attempt.id} · "
                        f"{row.attempt.amount_kopecks / 100:.2f} ₽ · "
                        f"{row.attempt.status}"
                    ),
                    callback_data=f"adminx:payment:{row.attempt.id}",
                )
            ]
        )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="←",
                callback_data=f"adminx:payments:{filter_name}:{page - 1}",
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="→",
                callback_data=f"adminx:payments:{filter_name}:{page + 1}",
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                text="← В панель",
                callback_data="adminx:home",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscriptions_keyboard(
    rows_data,
    *,
    filter_name: str,
    page: int,
    has_next: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="Активные",
                callback_data="adminx:subs:active:0",
            ),
            InlineKeyboardButton(
                text="Продление",
                callback_data="adminx:subs:renewal:0",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Отменены",
                callback_data="adminx:subs:cancelled:0",
            ),
            InlineKeyboardButton(
                text="Истекли",
                callback_data="adminx:subs:expired:0",
            ),
        ],
    ]

    for row in rows_data:
        username = (
            f"@{row.user.username}"
            if row.user.username
            else f"ID {row.user.id}"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"👑 {username} · {row.subscription.status}",
                    callback_data=f"admin:user:{row.user.id}",
                )
            ]
        )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="←",
                callback_data=f"adminx:subs:{filter_name}:{page - 1}",
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="→",
                callback_data=f"adminx:subs:{filter_name}:{page + 1}",
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                text="← В панель",
                callback_data="adminx:home",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_details_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Пользователь",
                    callback_data=f"admin:user:{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="← К платежам",
                    callback_data="adminx:payments:all:0",
                )
            ],
        ]
    )
