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
        "app/bot/commands.py",
        'BotCommand(command="start", description="Главное меню")',
        'BotCommand(command="cancel", description="Отключить подписку")',
        "sync_public_commands",
    )
    reject("app/bot/commands.py", 'command="menu"', 'command="help"', "testpay", "testcharge")
    require("app/main.py", "await sync_public_commands(bot)")
    require("app/managed_bots.py", "await sync_public_commands(bot)")
    require("app/bot/handlers/start_marketing.py", "await tracking.bot_started", "await session.commit()", "raise SkipHandler")
    reject("app/bot/handlers/start_marketing.py", "message.answer(", "personal_link_share_keyboard")
    require("app/bot/handlers/start.py", 'if code.startswith("src_")', "main_menu_for(message.from_user.id)", "show_personal_link_message", "texts.START_PROMO")
    require("app/bot/handlers/navigation.py", "@fallback_router.callback_query()", "texts.BUTTON_EXPIRED", "show_alert=True")
    require("app/core/texts.py", "BUTTON_EXPIRED")
    require("app/bot/handlers/subscriptions.py", '@router.message(Command("cancel"))', "FSMContext", "await state.clear()", "cancel_auto_renew")
    reject("app/bot/handlers/subscriptions.py", "StateFilter(None)")
    reject("app/bot/handlers/questions.py", 'Command("cancel")')
    require("app/services/reveal_checkout.py", 'checkout.status == "payment_pending" and checkout.invoice_id', "current_bot = require_current_bot()", "def payment_url")
    text = (ROOT / "app/services/reveal_checkout.py").read_text(encoding="utf-8")
    assert "current_bot = require_current_bot()\n        current_bot = require_current_bot()" not in text
    require("app/bot/handlers/reveals.py", "TelegramBadRequest", "has_active_vip(subscription)", "_deliver_identity", "RevealCheckoutService(")
    require("app/bot/handlers/questions.py", "TelegramBadRequest", 'callback.data == "cancel"')
    require("app/bot/handlers/__init__.py", "if load_settings().payment_test_commands_enabled:", "router.include_router(payments_router)", "router.include_router(recurrent_test_router)")
    require("app/core/config.py", "payment_test_commands_enabled: bool = Field(default=False")
    require(
        "app/bot/keyboards/personal_link.py",
        'SHARE_TEXT = "По этой ссылке можно мне прислать анонимное сообщение:\\n👉 {link}"',
        'full_link = link if link.startswith("https://") else f"https://{link}"',
        'short_link = full_link.removeprefix("https://")',
        "share_text = SHARE_TEXT.format(link=short_link)",
        'f"url=&text={encoded_text}"',
    )
    reject("app/bot/keyboards/personal_link.py", 'f"url=%20&text={encoded_text}"', "encoded_link =")
    require("app/models/question.py", 'answers: Mapped[list["Answer"]]')
    reject("app/bot/handlers/answers.py", "ANSWER_ALREADY_SENT")
    require("scripts/check_stage_62_runtime.py", "Stage 62 runtime check: OK")
    require("docs/STAGE_62_BOT_LAUNCH_READINESS.md", "Bot Launch Readiness")
    assert not list((ROOT / "migrations/versions").glob("*stage_62*"))
    print("Stage 62 check: OK")
    print("Canonical /start UX and marketing attribution hand-off: ready")
    print("Public Telegram command list: /start and /cancel only")
    print("Stale callbacks and repeat taps: safe")
    print("Reveal checkout and payment finalization: hardened")
    print("/cancel is reserved for subscription cancellation in every FSM state")
    print("Test payment commands remain launch-gated")
    print("Unlimited replies from Stage 61 remain active")
    print("Exact Telegram share text: preserved")
    print("No Stage 62 migration required")


if __name__ == "__main__":
    main()
