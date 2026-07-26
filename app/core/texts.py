"""User-facing copy for AnonMake.

Style rules:
- short;
- one clear action per message;
- light use of emoji;
- no technical details shown to users.
"""

WELCOME = (
    "💌 Анонимные сообщения\n\n"
    "Поделитесь своей ссылкой — и получайте сообщения без имени отправителя."
)

PERSONAL_LINK = "🔗 Ваша ссылка\n\n{link}"
PERSONAL_LINK_HINT = "Можно добавить её в профиль, канал или сторис."

INVALID_LINK = "Ссылка больше не действует"
SELF_MESSAGE = "Себе написать не получится 🙂"

QUESTION_PROMPT = "✍️ Напишите сообщение"
QUESTION_HINT = "Оно будет отправлено анонимно."
QUESTION_SENT = "✅ Отправлено"
QUESTION_EMPTY = "Напишите текст сообщения"
QUESTION_TOO_LONG = "Сообщение слишком длинное — максимум {limit} символов"
QUESTION_SESSION_EXPIRED = "Ссылка устарела. Откройте её ещё раз"
QUESTION_RECIPIENT_MISSING = "Получатель сейчас недоступен"
QUESTION_DELIVERY_FAILED = "Не удалось доставить сообщение"

NEW_QUESTION = "💌 Новое сообщение\n\n{text}"

ANSWER_PROMPT = "✍️ Напишите ответ"
ANSWER_SENT = "✅ Ответ отправлен"
ANSWER_EMPTY = "Напишите текст ответа"
ANSWER_TOO_LONG = "Ответ слишком длинный — максимум {limit} символов"
ANSWER_SESSION_EXPIRED = "Время ответа истекло"
ANSWER_NOT_FOUND = "Сообщение не найдено"
ANSWER_ALREADY_SENT = "На это сообщение уже ответили"
ANSWER_DELIVERY_FAILED = "Ответ сохранён, но доставить его не удалось"
ANSWER_RECEIVED = (
    "💬 Вам ответили\n\n"
    "Ваше сообщение:\n{question}\n\n"
    "Ответ:\n{answer}"
)

CANCELLED = "Отменено"
TEXT_ONLY = "Отправьте текстовое сообщение"

HELP = (
    "✨ Как это работает\n\n"
    "1. Скопируйте свою ссылку\n"
    "2. Поделитесь ею\n"
    "3. Получайте анонимные сообщения\n"
    "4. Отвечайте прямо в боте"
)

VIP_OFFER = (
    "👑 Узнайте, кто написал\n\n"
    "VIP открывает отправителей всех старых и новых сообщений "
    "по кнопке «Узнать кто это».\n\n"
    "Первый день — 1 ₽"
)
VIP_PAYMENT_UNAVAILABLE = "Оплата временно недоступна"
VIP_CONFIGURATION_ERROR = "Оплата пока не настроена"
VIP_SENDER = "👤 Отправитель: {sender}"
VIP_ACTIVATED = "✅ VIP активирован"
VIP_ACTIVATED_WITH_SENDER = "✅ VIP активирован\n\n👤 Отправитель: {sender}"
VIP_PAYMENT_PROCESSING = (
    "Платёж обрабатывается. Результат придёт в Telegram."
)
VIP_PAYMENT_FAILED = "Оплата не завершена"

TEMPORARY_ERROR = "Что-то пошло не так. Попробуйте ещё раз"
