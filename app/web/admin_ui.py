from __future__ import annotations

from datetime import datetime
from typing import Any

STATUS_LABELS = {
    # Subscriptions
    "trial_active": "Доступ активен",
    "active_1_day": "Доступ активен",
    "active_3_days": "Доступ активен",
    "past_due": "Ожидает оплаты",
    "payment_pending": "Обрабатывается",
    "cancelled_active": "Автопродление отключено",
    "expired": "Доступ завершён",
    "payment_method_blocked": "Способ оплаты недоступен",
    # Payments
    "success": "Успешно",
    "insufficient_funds": "Недостаточно средств",
    "pending": "Обрабатывается",
    "failed": "Ошибка",
    # Delivery and broadcasts
    "queued": "В очереди",
    "processing": "В работе",
    "sent": "Отправлено",
    "delivered": "Доставлено",
    "cancelled": "Отменено",
    "active": "Активен",
    "inactive": "В архиве",
    "alive": "Активен",
    "dead": "Недоступен",
}

STATUS_TONES = {
    "trial_active": "success",
    "active_1_day": "success",
    "active_3_days": "success",
    "success": "success",
    "sent": "success",
    "delivered": "success",
    "active": "success",
    "alive": "success",
    "past_due": "warning",
    "payment_pending": "warning",
    "insufficient_funds": "warning",
    "pending": "warning",
    "queued": "info",
    "processing": "info",
    "cancelled_active": "neutral",
    "cancelled": "neutral",
    "inactive": "neutral",
    "expired": "danger",
    "payment_method_blocked": "danger",
    "failed": "danger",
    "dead": "danger",
}

PAYMENT_KIND_LABELS = {
    "trial": "Открытие доступа",
    "primary": "Продление",
    "fallback": "Продление",
    "test_primary": "Тестовое продление",
    "test_fallback": "Тестовое продление",
    "admin_primary": "Ручное продление",
    "admin_fallback": "Ручное продление",
}

DELIVERY_KIND_LABELS = {
    "question": "Сообщение",
    "answer": "Ответ",
    "broadcast": "Рассылка",
    "payment": "Платёж",
}

AUDIT_ACTION_LABELS = {
    "subscription.manual_charge": "Ручное списание",
    "subscription.auto_renew": "Автопродление",
    "subscription.manual_extend": "Ручное продление",
    "source.create": "Создание источника",
    "source.delete": "Удаление источника",
    "broadcast.create": "Создание рассылки",
}


def money(kopecks: int | None) -> str:
    if kopecks is None:
        return "—"
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


def date_time(value: datetime | None, *, seconds: bool = False) -> str:
    if value is None:
        return "—"
    pattern = "%d.%m.%Y %H:%M:%S" if seconds else "%d.%m.%Y %H:%M"
    return value.strftime(pattern)


def date_only(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y") if value else "—"


def status_label(value: str | None) -> str:
    if not value:
        return "—"
    return STATUS_LABELS.get(value, value.replace("_", " ").capitalize())


def status_tone(value: str | None) -> str:
    return STATUS_TONES.get(value or "", "neutral")


def payment_kind(value: str | None) -> str:
    if not value:
        return "—"
    return PAYMENT_KIND_LABELS.get(value, value.replace("_", " ").capitalize())


def delivery_kind(value: str | None) -> str:
    if not value:
        return "—"
    return DELIVERY_KIND_LABELS.get(value, value.replace("_", " ").capitalize())


def audit_action(value: str | None) -> str:
    if not value:
        return "—"
    return AUDIT_ACTION_LABELS.get(value, value.replace(".", " · ").replace("_", " "))


def user_name(user: Any) -> str:
    username = getattr(user, "username", None)
    if username:
        return f"@{username}"
    first_name = getattr(user, "first_name", None)
    if first_name:
        return str(first_name)
    telegram_id = getattr(user, "telegram_id", None)
    return str(telegram_id) if telegram_id is not None else "Пользователь"


def yes_no(value: Any) -> str:
    return "Да" if bool(value) else "Нет"


def empty_text(entity: str) -> str:
    return f"{entity} пока нет."
