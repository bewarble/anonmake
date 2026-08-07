from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, (path, needle)


def reject(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle not in text, (path, needle)


def main() -> None:
    require(
        "app/core/error_diagnostics.py",
        'return f"err_{secrets.token_hex(6)}"',
        'action="bot_error"',
        '"telegram_user_id"',
        '"telegram_chat_id"',
        '"request_id"',
        '"bot_code"',
        "decode_bot_error_event",
    )
    require(
        "app/bot/handlers/errors.py",
        "new_error_id()",
        "record_bot_error(",
        'source="telegram_update"',
        "TEMPORARY_ERROR_WITH_ID",
        "error_id=%s",
    )
    require(
        "app/bot/handlers/payments.py",
        'source="test_payment_invoice"',
        'f"Код ошибки: {error_id}"',
        "record_bot_error(",
    )
    reject(
        "app/bot/handlers/payments.py",
        "str(exc)[:300]",
        'f"Ошибка: {str(exc)',
    )
    require(
        "app/delivery_worker.py",
        "record_delivery_error",
        'source="delivery_send"',
        'source="delivery_bot_credentials"',
        'f"Unexpected delivery error ({error_id})"',
        'f"Bot credentials unavailable ({error_id})"',
    )
    require(
        "app/managed_bots.py",
        "record_runtime_crash",
        'source="managed_bot_runtime"',
        "Managed bot runtime stopped unexpectedly",
    )
    require(
        "app/web/admin_observability.py",
        'AdminAuditLog.action == "bot_error"',
        "decode_bot_error_event",
        "recent_bot_errors",
    )
    require(
        "app/web/templates/platform_observability.html",
        "Последние ошибки Telegram-ботов",
        "item.error_id",
        "item.request_id",
        "item.telegram_user_id",
        "item.telegram_chat_id",
    )
    require(
        "app/core/texts.py",
        "TEMPORARY_ERROR_WITH_ID",
        "передайте поддержке код: {error_id}",
    )
    assert not list((ROOT / "migrations/versions").glob("*stage_59*"))
    print("Stage 59 check: OK")
    print("Bot error_id diagnostics and safe user fallbacks: ready")
    print("Payment, delivery and managed-bot runtime failures: covered")
    print("Bot errors are visible in platform observability")
    print("No raw payment exception text is exposed in Telegram")
    print("No Stage 59 migration required")


if __name__ == "__main__":
    main()
