from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
def recurrent_test_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Списать 299 ₽',callback_data='billingtest:choose:primary'),InlineKeyboardButton(text='Списать 99 ₽',callback_data='billingtest:choose:fallback')],[InlineKeyboardButton(text='Отмена',callback_data='billingtest:cancel')]])
def recurrent_test_confirm(kind: str, amount: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'✅ Подтвердить {amount} ₽',callback_data=f'billingtest:confirm:{kind}')],[InlineKeyboardButton(text='← Назад',callback_data='billingtest:back'),InlineKeyboardButton(text='Отмена',callback_data='billingtest:cancel')]])
