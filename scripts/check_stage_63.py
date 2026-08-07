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
        "app/core/texts.py",
        "🚀 Здесь можно отправить анонимное сообщение человеку, который опубликовал эту ссылку.",
        "✅ Сообщение отправлено, ожидайте ответ от человека!",
        "💬 Начни получать анонимные сообщения прямо сейчас!",
        "Разместите ссылку у себя в профиле и вам смогут написать ваши друзья и знакомые ✍️",
        "<b>📨 Вам отправили новое анонимное сообщение</b>",
        "💬 Напишите свой ответ на данное сообщение:",
        "✅ Ответ успешно отправлен и уже пришёл человеку!",
        "❗️ У вас не найдено активных подписок.",
        "✅ Авто-продление успешно отключено!",
        "Стоимость пробной подписки 1₽ за 1 день доступа.",
        "https://sms.mooncloud.ltd/terms",
        "https://sms.mooncloud.ltd/privacy",
        "https://sms.mooncloud.ltd/pricing",
    )
    require("app/bot/commands.py", 'BotCommand(command="cancel", description="Отключить подписку")')
    require(
        "app/bot/ui.py",
        'USER_PERSONAL_LINK = "💬 Начать получать сообщения"',
        'ACTION_CANCEL = "✖️ Отменить"',
        'QUESTION_ANSWER = "💬 Ответить"',
        'QUESTION_REVEAL = "👁️ Узнать кто это"',
    )
    reject("app/bot/ui.py", "USER_HELP")
    require("app/bot/keyboards/main_menu.py", "KeyboardButton(text=USER_PERSONAL_LINK)", "is_persistent=True")
    reject("app/bot/keyboards/main_menu.py", "USER_HELP")
    require("app/models/user.py", "PUBLIC_CODE_LENGTH = 8", "PUBLIC_CODE_ALPHABET", "secrets.choice(PUBLIC_CODE_ALPHABET)")
    require(
        "migrations/versions/20260807_0021_short_public_codes.py",
        'revision = "20260807_0021"',
        'down_revision = "20260807_0020"',
        "_regenerate(8)",
    )
    require(
        "app/bot/keyboards/questions.py",
        "CopyTextButton",
        'text="✍️ Написать ещё"',
        'text="🔗 Скопировать ссылку"',
        'text="📤 Выложить в каналы / чаты"',
        'callback_data=f"ask_again:{recipient_id}"',
        "CopyTextButton(text=full_link)",
        "text=QUESTION_ANSWER",
        "text=QUESTION_REVEAL",
    )
    require(
        "app/bot/keyboards/personal_link.py",
        'text="🔗 Скопировать ссылку"',
        'text="📤 Выложить в каналы / чаты"',
        "CopyTextButton(text=full_link)",
        '"https://t.me/share/url/?"',
    )
    require(
        "app/bot/handlers/start.py",
        "texts.START_PROMO.format",
        'link.removeprefix("https://")',
        "texts.SELF_MESSAGE",
        "personal_link_share_keyboard(link)",
        "reply_markup=main_menu_for(message.from_user.id)",
        "disable_web_page_preview=True",
    )
    reject("app/bot/handlers/start.py", 'await message.answer(\n            "💬",')
    reject("app/bot/handlers/navigation.py", "USER_HELP", "show_help")
    require(
        "app/bot/handlers/subscriptions.py",
        '@router.message(Command("cancel"))',
        "if subscription.auto_renew:",
        "await repository.cancel_auto_renew(subscription, cancelled_at=now)",
        "texts.NO_ACTIVE_ACCESS",
        "texts.AUTO_RENEW_OFF",
    )
    require(
        "app/bot/handlers/reveals.py",
        "texts.REVEAL_CONSENT",
        'parse_mode="HTML"',
        "disable_web_page_preview=True",
    )
    require(
        "app/bot/handlers/questions.py",
        '@router.callback_query(F.data.startswith("ask_again:"))',
        "write_more_keyboard(recipient.id)",
        'texts.QUESTION_PROMO.format(link=personal_link.removeprefix("https://"))',
        "personal_link_share_keyboard(personal_link)",
        'payload["parse_mode"] = "HTML"',
        "html.escape(question.text)",
        "current_state == AskQuestion.waiting_for_text.state",
        "await callback.message.delete()",
        "disable_web_page_preview=True",
    )
    require(
        "app/bot/handlers/answers.py",
        "answer_share_keyboard(personal_link)",
        "texts.ANSWER_PROMPT",
        "texts.ANSWER_SENT",
        "texts.ANSWER_RECEIVED.format(answer=html.escape(text))",
        'payload={"parse_mode": "HTML"}',
    )
    require(
        "app/services/admin_statistics_stage25.py",
        "bot_id = require_current_bot().id",
        "User.bot_id == bot_id",
        "DeliveryOutbox.bot_id == bot_id",
        "PaymentMethod.bot_id == bot_id",
    )
    require(
        "app/core/admin_metrics.py",
        "return require_current_bot().id",
        "User.bot_id == self.bot_id",
        "DeliveryOutbox.bot_id == self.bot_id",
        "PaymentAttempt.bot_id == self.bot_id",
    )
    require(
        "app/repositories/marketing.py",
        "TrafficSource.bot_id == bot_id",
        "Broadcast.bot_id == require_current_bot().id",
        "User.bot_id == bot_id",
        "Subscription.bot_id == bot_id",
    )
    require(
        "app/broadcast_worker.py",
        "User.bot_id == item.bot_id",
        "Subscription.bot_id == item.bot_id",
        "bot_id=item.bot_id",
    )
    require(
        "app/bot/handlers/admin_stage25_1.py",
        "• Живые —",
        "• Мертвые —",
        "♻️ <b>Прирост</b>",
        "📈 <b>Саморост</b>",
    )
    require("app/delivery_worker.py", 'parse_mode = payload.get("parse_mode")', "parse_mode=parse_mode")
    print("Stage 63 check: OK")
    print("Public codes: shortened to 8 characters")
    print("Public menu: one persistent action")
    print("/start: single promo message without inline actions")
    print("All other promo cards: native copy/share actions")
    print("Anonymous question/answer actions: 💬 Ответить + 👁️ Узнать кто это")
    print("/cancel command label: Отключить подписку")
    print("Telegram admin statistics/export/profit/sources/broadcasts: scoped to current bot")
    print("Reveal consent: Mooncloud terms/privacy/pricing links")
    print("Question and answer UX: final")
    print("Stage 63 migration: 20260807_0021_short_public_codes")


if __name__ == "__main__":
    main()
