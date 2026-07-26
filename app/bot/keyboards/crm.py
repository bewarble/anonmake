from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def crm_user_keyboard(user_id: int, tags) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="📝 Добавить заметку",
                callback_data=f"crm:note:{user_id}",
            ),
            InlineKeyboardButton(
                text="🏷 Добавить тег",
                callback_data=f"crm:tag:{user_id}",
            ),
        ]
    ]

    for tag in tags[:6]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✕ {tag.name}",
                    callback_data=f"crm:untag:{user_id}:{tag.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="← К пользователю",
                callback_data=f"admin:user:{user_id}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def crm_open_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗂 CRM",
                    callback_data=f"crm:user:{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Пользователи",
                    callback_data="adminx:users:recent:0",
                )
            ],
        ]
    )
