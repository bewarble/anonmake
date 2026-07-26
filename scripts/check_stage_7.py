from app.core import texts
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.questions import answer_question_keyboard
from app.bot.keyboards.reveals import reveal_checkout_keyboard

assert len(texts.WELCOME) < 220
assert len(texts.VIP_OFFER) < 260
assert "────────────────" not in texts.NEW_QUESTION
assert "👤 Отправитель:" in texts.VIP_SENDER

menu = main_menu_keyboard()
assert len(menu.keyboard) == 2

question_keyboard = answer_question_keyboard(1)
assert len(question_keyboard.inline_keyboard) == 1
assert len(question_keyboard.inline_keyboard[0]) == 2

checkout = reveal_checkout_keyboard(
    payment_url="https://example.com/pay",
    offer_url="https://example.com/offer",
)
assert checkout.inline_keyboard[0][0].text == "Открыть за 1 ₽"
assert checkout.inline_keyboard[1][0].text == "Условия"

print("Stage 7 check: OK")
print("Style: compact, consistent, emoji-light")
print("Question actions: one-row layout")
print("User profile/settings/referrals: not added")
