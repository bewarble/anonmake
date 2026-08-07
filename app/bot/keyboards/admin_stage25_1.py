from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.ui import (
    ACTION_BACK_TO_LIST,
    ACTION_CANCEL,
    ACTION_DELETE,
    BROADCAST_ALL,
    BROADCAST_WITH_ACCESS,
    BROADCAST_WITHOUT_ACCESS,
    EXPORT_ALIVE,
    EXPORT_ALL,
    SOURCE_CREATE,
)

SOURCE_PAGE_SIZE = 7


def broadcast_audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BROADCAST_ALL, callback_data="admin25:broadcast:audience:all")],
            [
                InlineKeyboardButton(text=BROADCAST_WITH_ACCESS, callback_data="admin25:broadcast:audience:vip"),
                InlineKeyboardButton(text=BROADCAST_WITHOUT_ACCESS, callback_data="admin25:broadcast:audience:non_vip"),
            ],
            [InlineKeyboardButton(text=ACTION_CANCEL, callback_data="admin25:broadcast:cancel")],
        ]
    )


def referrals_keyboard(sources, *, page: int = 0) -> InlineKeyboardMarkup:
    total = len(sources)
    pages = max((total + SOURCE_PAGE_SIZE - 1) // SOURCE_PAGE_SIZE, 1)
    page = min(max(page, 0), pages - 1)
    start = page * SOURCE_PAGE_SIZE
    visible = sources[start : start + SOURCE_PAGE_SIZE]

    rows = [
        [InlineKeyboardButton(text=source.name, callback_data=f"adminm:source:{source.id}")]
        for source in visible
    ]
    rows.append([InlineKeyboardButton(text="Добавить реф. ссылку", callback_data="adminm:source:create")])
    if pages > 1:
        rows.append(
            [
                InlineKeyboardButton(text="<-", callback_data=f"admin25:referrals:page:{max(page - 1, 0)}"),
                InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="admin25:referrals:noop"),
                InlineKeyboardButton(text="->", callback_data=f"admin25:referrals:page:{min(page + 1, pages - 1)}"),
            ]
        )
    rows.append([InlineKeyboardButton(text=ACTION_CANCEL, callback_data="admin25:referrals:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def referral_card_keyboard(source_id: int, *, page: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Назад", callback_data=f"admin25:referrals:page:{page}"),
                InlineKeyboardButton(text="Удалить", callback_data=f"source:delete:{source_id}"),
            ],
        ]
    )


def export_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=EXPORT_ALL, callback_data="admin25:export:all")],
            [InlineKeyboardButton(text=EXPORT_ALIVE, callback_data="admin25:export:alive")],
            [InlineKeyboardButton(text=ACTION_CANCEL, callback_data="admin25:cancel:export")],
        ]
    )


def referral_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ACTION_BACK_TO_LIST, callback_data="admin25:referrals")]
        ]
    )
