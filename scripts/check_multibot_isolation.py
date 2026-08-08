from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    body = text(path)
    for needle in needles:
        assert needle in body, (path, needle)


def reject(path: str, *needles: str) -> None:
    body = text(path)
    for needle in needles:
        assert needle not in body, (path, needle)


def main() -> None:
    require(
        "app/bot/storage.py",
        "DefaultKeyBuilder(with_bot_id=True)",
    )
    require(
        "app/repositories/users.py",
        "User.id == user_id",
        "User.bot_id == bot_id",
        "bot_id = require_current_bot().id",
    )
    require(
        "app/repositories/questions.py",
        "sender.bot_id == bot_id",
        "recipient.bot_id == bot_id",
        'raise ValueError("Question participants must belong to the current bot")',
    )
    require(
        "app/repositories/marketing.py",
        "resolved_bot_id = bot_id if bot_id is not None else require_current_bot().id",
        "TrafficSource.bot_id == require_current_bot().id",
        "Broadcast.bot_id == require_current_bot().id",
    )
    reject(
        "app/repositories/marketing.py",
        "order_by(BotInstance.id).limit(1)",
        "No active bot instance is available",
    )
    require(
        "app/broadcast_worker.py",
        "User.bot_id == item.bot_id",
        "bot_id=item.bot_id",
    )
    require(
        "app/delivery_worker.py",
        "User.bot_id == job.bot_id",
    )
    require(
        "app/repositories/billing.py",
        "PaymentMethod.bot_id == bot_id",
        "Subscription.bot_id == bot_id",
        "PaymentAttempt.bot_id == bot_id",
    )
    require(
        "app/services/billing_worker.py",
        "set_current_bot(",
        "subscription.bot_id",
        "reset_current_bot(context_token)",
    )
    require(
        "app/bot/handlers/reveals.py",
        "load_impaya_config(session, settings, current_bot.id)",
        "create_impaya_client(impaya_config)",
        "impaya_config.payment_form_url_template",
    )
    require(
        "app/services/payment_notifications.py",
        "load_impaya_config(session, settings, instance.id)",
        "create_impaya_client(impaya_config)",
        "resolve_bot_token(session, settings, instance)",
    )
    require(
        "app/web/subscription_payments.py",
        "load_impaya_config(session, settings, instance.id)",
        "create_impaya_client(impaya_config)",
    )
    require(
        "app/web/admin.py",
        "ScopedWebAdminRepository(",
        "bot_id=selected_bot_id(request)",
    )
    require(
        "app/web/admin_scoped_repository.py",
        "User.bot_id == self.bot_id",
        "PaymentAttempt.bot_id == self.bot_id",
        "TrafficSource.bot_id == self.bot_id",
        "DeliveryOutbox.bot_id == self.bot_id",
    )

    print("Multibot isolation contract check: OK")
    print("FSM state: bot-id isolated")
    print("Users/questions/sources/broadcasts: project scoped")
    print("Billing/reveal callbacks: owning project scoped")
    print("Web admin users/payments/sources/delivery: selected project scoped")


if __name__ == "__main__":
    main()
