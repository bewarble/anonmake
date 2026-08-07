"""AnonMake product language.

User-facing copy follows three rules:
1. Short and clear.
2. No billing internals, renewal amounts, technical codes or dates.
3. The public offer is always described as: 1 ₽ — 1 day of VIP status.
"""

# Global
READY = "✅ Готово."
CANCELLED = "ℹ️ Действие отменено."
TEMPORARY_ERROR = "❌ Что-то пошло не так.\n\nПопробуйте ещё раз."
TEMPORARY_ERROR_WITH_ID = (
    "❌ Что-то пошло не так.\n\n"
    "Попробуйте ещё раз. Если ошибка повторится, передайте поддержке код: {error_id}"
)
TEXT_ONLY = "ℹ️ Этот тип сообщения пока не поддерживается."
UNKNOWN_INPUT = "ℹ️ Выберите действие в меню ниже."
BUTTON_EXPIRED = "ℹ️ Эта кнопка больше не актуальна.\n\nОткройте нужное действие заново."

# Start and personal link
WELCOME = (
    "👋 Добро пожаловать!\n\n"
    "Здесь можно получать анонимные сообщения и отвечать на них прямо в Telegram."
)
START_PROMO = (
    "💬 Начни получать анонимные сообщения прямо сейчас!\n\n"
    "Твоя ссылка:\n"
    "👉 {link}\n\n"
    "Добавь эту ссылку ☝️ в описание профиля Telegram/TikTok/Instagram и в истории, чтобы получать послания 💌"
)
PERSONAL_LINK = "🔗 Ваша ссылка\n\n{link}"
PERSONAL_LINK_HINT = "Поделитесь ссылкой с друзьями или опубликуйте её в канале."
LINK_COPIED_HINT = "Нажмите на ссылку, чтобы скопировать её."
HELP = (
    "🤫 Чтобы получать сообщения — добавь ссылку в свой профиль!\n\n"
    "Пример как на фото 👇"
)
INVALID_LINK = "⚠️ Эта ссылка больше не работает."
SELF_MESSAGE = "Разместите ссылку у себя в профиле и вам смогут написать ваши друзья и знакомые ✍️"

# Questions
QUESTION_PROMPT = (
    "🚀 Здесь можно отправить анонимное сообщение человеку, который опубликовал эту ссылку.\n\n"
    "🖊 Напишите сюда всё, что хотите ему передать, и через несколько секунд он получит ваше сообщение, "
    "но не будет знать от кого.\n\n"
    "Отправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷 видеосообщения (кружки), а также ✨ стикеры."
)
QUESTION_HINT = ""
QUESTION_SENT = "✅ Сообщение отправлено, ожидайте ответ от человека!"
QUESTION_PROMO = (
    "💬 Начни получать анонимные сообщения прямо сейчас!\n\n"
    "Твоя ссылка:\n"
    "👉 {link}\n\n"
    "Добавь эту ссылку ☝️ в описание профиля Telegram/TikTok/Instagram и в истории, чтобы получать сообщения 💌"
)
QUESTION_EMPTY = "ℹ️ Напишите текст сообщения."
QUESTION_TOO_LONG = "⚠️ Сообщение слишком длинное.\n\nМаксимум: {limit} символов."
QUESTION_SESSION_EXPIRED = "⚠️ Ссылка устарела.\n\nОткройте её ещё раз."
QUESTION_RECIPIENT_MISSING = "⚠️ Получатель сейчас недоступен."
QUESTION_DELIVERY_FAILED = "❌ Не удалось отправить сообщение.\n\nПопробуйте позже."
QUESTION_TOO_FAST = "⚠️ Слишком быстро.\n\nПодождите пару секунд."
QUESTION_DUPLICATE = "ℹ️ Такое сообщение уже отправлено."
NEW_QUESTION = "<b>📨 Вам отправили новое анонимное сообщение</b>\n\n{text}"
NEW_QUESTION_HEADER = "<b>📨 Вам отправили новое анонимное сообщение</b>"

# Answers
ANSWER_PROMPT = "💬 Напишите свой ответ на данное сообщение:"
ANSWER_SENT = (
    "✅ Ответ успешно отправлен и уже пришёл человеку!\n\n"
    "💬 Ожидай от него ответ!\n\n"
    "💝 Хочешь получать больше сообщений? Поделись ссылкой:"
)
ANSWER_EMPTY = "ℹ️ Напишите текст ответа."
ANSWER_TOO_LONG = "⚠️ Ответ слишком длинный.\n\nМаксимум: {limit} символов."
ANSWER_SESSION_EXPIRED = "⚠️ Время ответа истекло."
ANSWER_NOT_FOUND = "⚠️ Сообщение не найдено."
ANSWER_ALREADY_SENT = "ℹ️ Вы уже ответили на это сообщение."
ANSWER_DELIVERY_FAILED = "ℹ️ Ответ сохранён.\n\nМы доставим его автоматически."
ANSWER_RECEIVED = "💬 Вам ответили\n\n{answer}"

# Access and payment
ACCESS_OFFER = (
    "👑 VIP подписка\n\n"
    "Узнавайте отправителей старых и новых сообщений.\n\n"
    "1 ₽ — 1 день VIP статуса."
)
ACCESS_ACTIVE = "👑 VIP статус активирован."
ACCESS_ACTIVE_WITH_SENDER = "👑 VIP статус активирован.\n\n👤 Отправитель: {sender}"
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
NO_ACTIVE_ACCESS = "ℹ️ Активной VIP подписки нет."
AUTO_RENEW_ALREADY_OFF = "ℹ️ Автопродление уже отключено."
AUTO_RENEW_CONFIRM = (
    "⚙️ Отключить автопродление?\n\n"
    "VIP статус останется активным."
)
AUTO_RENEW_OFF = "✅ Автопродление отключено.\n\nVIP статус останется активным."
AUTO_RENEW_KEEP = "✅ Автопродление оставлено включённым."


REVEAL_CONSENT = (
    "👉 Стоимость пробной VIP подписки — 1 ₽ за 1 день VIP статуса.\n\n"
    "Выбирая любой из тарифов, вы соглашаетесь с автоматической пролонгацией 299 ₽ каждые 3 дня "
    "по истечению оплаченного периода. Возможно частичное списание 99 ₽ за 1 день VIP статуса.\n\n"
    "Продолжая оплату, вы соглашаетесь с "
    '<a href="https://sms.evocloud.su/terms">условиями пользования</a>.'
)
REVEAL_PAYMENT_READY = "Нажмите кнопку ниже, чтобы перейти к оплате."

QUESTION_MEDIA_TOO_LARGE = "⚠️ Файл слишком большой для отправки."
