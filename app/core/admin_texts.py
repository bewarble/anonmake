"""Consistent administrator-facing Telegram copy."""

DENIED = "⚠️ Действие недоступно."
INVALID_DATA = "⚠️ Некорректные данные."
SESSION_EXPIRED = "⚠️ Сессия истекла.\n\nНачните действие заново."
CANCELLED = "ℹ️ Действие отменено."

STATISTICS_TITLE = "📊 <b>Общая статистика</b>"
PROFIT_TITLE = "💰 <b>Прибыль</b>"
EXPORT_TITLE = "📦 <b>Выгрузка</b>"
SOURCES_TITLE = "🔗 <b>Источники</b>"
BROADCAST_TITLE = "📣 <b>Рассылка</b>"

EXPORT_PROMPT = "📦 <b>Выгрузка</b>\n\nВыберите аудиторию."
EXPORT_READY_ALL = "✅ Выгрузка всех пользователей готова."
EXPORT_READY_ALIVE = "✅ Выгрузка активных пользователей готова."

SOURCES_EMPTY = "Источников пока нет."
SOURCES_PROMPT = "Выберите источник или создайте новый."
SOURCE_NOT_FOUND = "⚠️ Источник не найден."
SOURCE_NAME_PROMPT = "✍️ Введите название источника."
SOURCE_NAME_EMPTY = "⚠️ Укажите название."
SOURCE_NAME_LONG = "⚠️ Название слишком длинное.\n\nМаксимум: 120 символов."
SOURCE_URL_PROMPT = "🔗 Отправьте ссылку на источник."
SOURCE_URL_INVALID = "⚠️ Отправьте корректную ссылку с http:// или https://."
SOURCE_URL_LONG = "⚠️ Ссылка слишком длинная."
SOURCE_SPEND_PROMPT = "💰 Укажите сумму закупки в рублях.\n\nНапример: 15000"
SOURCE_SPEND_INVALID = "⚠️ Введите корректную сумму."
SOURCE_SPEND_LARGE = "⚠️ Сумма слишком большая."
SOURCE_CREATED = "✅ Источник создан."
SOURCE_CREATE_CANCELLED = "ℹ️ Создание источника отменено."
SOURCE_DELETE_PROMPT = (
    "🗑 <b>Удалить источник?</b>\n\n"
    "{name}\n\n"
    "Ссылка будет отключена, а статистика сохранится."
)
SOURCE_DELETED = "✅ Источник отключён."
SOURCE_ALREADY_DELETED = "ℹ️ Источник уже отключён."

BROADCAST_AUDIENCE_PROMPT = "📣 <b>Рассылка</b>\n\nВыберите аудиторию."
BROADCAST_TEXT_PROMPT = (
    "✍️ Отправьте текст рассылки.\n\n"
    "Чтобы выйти, нажмите «Отмена» или отправьте /cancel."
)
BROADCAST_TEXT_EMPTY = "⚠️ Текст не может быть пустым."
BROADCAST_TEXT_LONG = "⚠️ Текст слишком длинный.\n\nМаксимум: 4000 символов."
BROADCAST_PREVIEW_NOTE = "Это предпросмотр. В рассылке кнопка будет рабочей."
BROADCAST_QUEUED = "✅ Рассылка #{item_id} добавлена в очередь."
BROADCAST_CANCELLED = "ℹ️ Рассылка отменена."
