"""AnonMake product language.

User-facing copy follows three rules:
1. Short and clear.
2. No billing internals, renewal amounts, technical codes or dates.
3. The public offer is always described as: 1 ₽ — 1 day of access.
"""

# Global
READY = "✅ Готово."
CANCELLED = "ℹ️ Действие отменено."
TEMPORARY_ERROR = "❌ Что-то пошло не так.\n\nПопробуйте ещё раз."
TEXT_ONLY = "ℹ️ Этот тип сообщения пока не поддерживается."

# Start and personal link
WELCOME = ""
PERSONAL_LINK = "🔗 Ваша ссылка\n\n{link}"
PERSONAL_LINK_HINT = "Поделитесь ссылкой с друзьями или опубликуйте её в канале."
LINK_COPIED_HINT = "Нажмите на ссылку, чтобы скопировать её."

HELP = (
    "✨ Как всё работает\n\n"
    "1. Поделитесь своей ссылкой\n"
    "2. Получайте анонимные сообщения\n"
    "3. Отвечайте прямо в боте"
)

INVALID_LINK = "⚠️ Эта ссылка больше не работает."
SELF_MESSAGE = "🙂 Себе написать не получится."

# Questions
QUESTION_PROMPT = "✍️ Отправьте текст, фото, видео, файл, голосовое или стикер."
QUESTION_HINT = "Отправитель останется анонимным."
QUESTION_SENT = "✅ Сообщение отправлено."
QUESTION_EMPTY = "ℹ️ Напишите текст сообщения."
QUESTION_TOO_LONG = "⚠️ Сообщение слишком длинное.\n\nМаксимум: {limit} символов."
QUESTION_SESSION_EXPIRED = "⚠️ Ссылка устарела.\n\nОткройте её ещё раз."
QUESTION_RECIPIENT_MISSING = "⚠️ Получатель сейчас недоступен."
QUESTION_DELIVERY_FAILED = "❌ Не удалось отправить сообщение.\n\nПопробуйте позже."
QUESTION_TOO_FAST = "⚠️ Слишком быстро.\n\nПодождите пару секунд."
QUESTION_DUPLICATE = "ℹ️ Такое сообщение уже отправлено."
NEW_QUESTION = "💌 Новое сообщение\n\n{text}"

# Answers
ANSWER_PROMPT = "✍️ Напишите ответ."
ANSWER_SENT = "✅ Ответ отправлен."
ANSWER_EMPTY = "ℹ️ Напишите текст ответа."
ANSWER_TOO_LONG = "⚠️ Ответ слишком длинный.\n\nМаксимум: {limit} символов."
ANSWER_SESSION_EXPIRED = "⚠️ Время ответа истекло."
ANSWER_NOT_FOUND = "⚠️ Сообщение не найдено."
ANSWER_ALREADY_SENT = "ℹ️ Вы уже ответили на это сообщение."
ANSWER_DELIVERY_FAILED = "ℹ️ Ответ сохранён.\n\nМы доставим его автоматически."
ANSWER_RECEIVED = "💬 Вам ответили\n\n{answer}"

# Access and payment
ACCESS_OFFER = (
    "⭐ Доступ\n\n"
    "Узнавайте отправителей старых и новых сообщений.\n\n"
    "1 ₽ — 1 день доступа."
)
ACCESS_ACTIVE = "✅ Доступ открыт."
ACCESS_ACTIVE_WITH_SENDER = "✅ Доступ открыт.\n\n👤 Отправитель: {sender}"
ACCESS_PAYMENT_PROCESSING = "⏳ Оплата обрабатывается.\n\nОбычно это занимает несколько секунд."
ACCESS_PAYMENT_FAILED = "❌ Оплата не завершена.\n\nПопробуйте ещё раз."
ACCESS_PAYMENT_UNAVAILABLE = "⚠️ Оплата временно недоступна."
ACCESS_CONFIGURATION_ERROR = "⚠️ Оплата пока недоступна."
ACCESS_SENDER = "👤 Отправитель: {sender}"

# Compatibility aliases for existing handlers.
VIP_OFFER = ACCESS_OFFER
VIP_PAYMENT_UNAVAILABLE = ACCESS_PAYMENT_UNAVAILABLE
VIP_CONFIGURATION_ERROR = ACCESS_CONFIGURATION_ERROR
VIP_SENDER = ACCESS_SENDER
VIP_ACTIVATED = ACCESS_ACTIVE
VIP_ACTIVATED_WITH_SENDER = ACCESS_ACTIVE_WITH_SENDER
VIP_PAYMENT_PROCESSING = ACCESS_PAYMENT_PROCESSING
VIP_PAYMENT_FAILED = ACCESS_PAYMENT_FAILED

# Subscription cancellation
NO_ACTIVE_ACCESS = "ℹ️ Активного доступа нет."
AUTO_RENEW_ALREADY_OFF = "ℹ️ Автопродление уже отключено."
AUTO_RENEW_CONFIRM = (
    "⚙️ Отключить автопродление?\n\n"
    "Доступ останется активным."
)
AUTO_RENEW_OFF = "✅ Автопродление отключено.\n\nДоступ останется активным."
AUTO_RENEW_KEEP = "✅ Автопродление оставлено включённым."


REVEAL_CONSENT = (
    "👉 Стоимость пробной подписки 1₽ за 1 день доступа.\n\n"
    "Выбирая любой из тарифов, вы соглашаетесь с автоматической пролонгацией 299 ₽ каждые 3 дня "
    "по истечению оплаченного периода. Возможно частичное списание 99 ₽ за 1 день доступа.\n\n"
    "Продолжая оплату, вы соглашаетесь с "
    '<a href="https://sms.evocloud.su/terms">условиями пользования</a>.'
)
REVEAL_PAYMENT_READY = "Нажмите кнопку ниже, чтобы перейти к оплате."

QUESTION_MEDIA_TOO_LARGE = "⚠️ Файл слишком большой для отправки."
