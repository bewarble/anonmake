from prometheus_client import Counter, Histogram

TELEGRAM_UPDATES = Counter(
    "anonmake_telegram_updates_total",
    "Telegram updates processed",
    ["status"],
)

QUESTIONS_SENT = Counter(
    "anonmake_questions_sent_total",
    "Anonymous questions sent",
)

ANSWERS_SENT = Counter(
    "anonmake_answers_sent_total",
    "Answers sent",
)

PAYMENT_CALLBACKS = Counter(
    "anonmake_payment_callbacks_total",
    "Payment callbacks received",
    ["status"],
)

PAYMENT_RECONCILIATION_SECONDS = Histogram(
    "anonmake_payment_reconciliation_seconds",
    "Time spent reconciling a payment",
)
