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
    require(
        "app/models/user.py",
        "PUBLIC_CODE_MIN_LENGTH = 5",
        "PUBLIC_CODE_MAX_LENGTH = 6",
        "secrets.choice((PUBLIC_CODE_MIN_LENGTH, PUBLIC_CODE_MAX_LENGTH))",
        "PUBLIC_CODE_ALPHABET",
        "is_blocked: Mapped[bool]",
        "blocked_at: Mapped[datetime | None]",
    )
    require(
        "app/repositories/users.py",
        "PUBLIC_CODE_CREATE_ATTEMPTS = 20",
        "public_code=generate_public_code()",
        "for _ in range(PUBLIC_CODE_CREATE_ATTEMPTS):",
        'raise RuntimeError("Could not allocate a unique public code")',
        "user.is_blocked = False",
        "async def set_block_state(",
        "user.is_blocked = is_blocked",
    )
    require(
        "migrations/versions/20260807_0021_short_public_codes.py",
        'revision = "20260807_0021"',
        'down_revision = "20260807_0020"',
        "_regenerate(8)",
    )
    require(
        "migrations/versions/20260808_0022_user_block_state.py",
        'revision = "20260808_0022"',
        'down_revision = "20260807_0021"',
        'sa.Column("is_blocked"',
        'sa.Column("blocked_at"',
        "latest_failure",
    )
    require(
        "migrations/versions/20260808_0023_random_short_public_codes.py",
        'revision = "20260808_0023"',
        'down_revision = "20260808_0022"',
        "_regenerate(5, 6)",
        "_regenerate(8, 8)",
    )
    require(
        "app/bot/keyboards/questions.py",
        'text="✍️ Написать ещё"',
        'callback_data=f"ask_again:{recipient_id}"',
        "text=QUESTION_ANSWER",
        "text=QUESTION_REVEAL",
        "return personal_link_share_keyboard(link)",
    )
    require(
        "app/bot/keyboards/personal_link.py",
        'SHARE_TEXT = "По этой ссылке можно мне прислать анонимное сообщение:\\n👉 {link}"',
        'text="🔗 Скопировать ссылку"',
        'text="📤 Выложить в каналы / чаты"',
        "CopyTextButton(text=full_link)",
        'short_link = full_link.removeprefix("https://")',
        'f"url=&text={encoded_text}"',
    )
    reject("app/bot/keyboards/personal_link.py", 'f"url=%20&text={encoded_text}"', "encoded_link =")
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
        "app/bot/handlers/chat_members.py",
        "@router.my_chat_member()",
        'BLOCKED_STATUSES = {"kicked", "left"}',
        "set_block_state(",
    )
    require("app/main.py", "dispatcher.my_chat_member.outer_middleware(database_middleware)")
    require("app/managed_bots.py", "dispatcher.my_chat_member.outer_middleware(middleware)")
    require(
        "app/services/admin_statistics_stage25.py",
        "bot_id = require_current_bot().id",
        "User.bot_id == bot_id",
        "User.is_blocked.is_(True)",
        "User.blocked_at >= left",
        "PaymentMethod.bot_id == bot_id",
    )
    require(
        "app/core/admin_metrics.py",
        "return require_current_bot().id",
        "User.bot_id == self.bot_id",
        "User.is_blocked.is_(False)",
        "PaymentAttempt.bot_id == self.bot_id",
    )
    require(
        "app/services/admin_charts_stage25.py",
        'label="Пользователи"',
        'label="Заблокированные"',
        'label="Оборот"',
        '_date_range_title(labels, "Статистика")',
        '_date_range_title(labels, "Оборот")',
        "_label_bars(axis, joined_bars",
        "_label_bars(axis, blocked_bars",
        "_label_bars(axis, bars",
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
        "async def delete_message_quietly",
        "await delete_message_quietly(message)",
        "await delete_message_quietly(callback.message)",
        "await callback.message.answer_document",
        "await callback.message.answer(admin_texts.BROADCAST_TEXT_PROMPT",
    )
    require(
        "app/bot/handlers/admin_marketing.py",
        "async def delete_message_quietly",
        "await delete_message_quietly(callback.message)",
        "await callback.message.answer(admin_texts.BROADCAST_QUEUED.format",
    )
    require(
        "app/bot/handlers/source_management.py",
        "async def delete_message_quietly",
        "await delete_message_quietly(callback.message)",
    )
    reject("app/bot/handlers/admin_marketing.py", "edit_text(admin_texts.BROADCAST_CANCELLED)")
    require(
        "app/delivery_worker.py",
        'parse_mode = payload.get("parse_mode")',
        "parse_mode=parse_mode",
        "mark_user_blocked_fallback",
        "user.is_blocked = True",
    )
    print("Stage 63 check: OK")
    print("Public codes: random 5-6 characters with collision retry")
    print("Public menu: one persistent action")
    print("/start: single promo message without inline actions")
    print("All other promo cards: native copy/share actions with canonical text")
    print("Anonymous question/answer actions: 💬 Ответить + 👁️ Узнать кто это")
    print("/cancel command label: Отключить подписку")
    print("Telegram admin statistics/export/profit/sources/broadcasts: scoped to current bot")
    print("Telegram admin navigation: replace-style messages; cancel deletes silently")
    print("Alive/dead users: live Telegram my_chat_member state with delivery fallback")
    print("Admin charts: labeled daily users/blocked and turnover series")
    print("Reveal consent: Mooncloud terms/privacy/pricing links")
    print("Question and answer UX: final")
    print("Stage 63 migrations: short public codes + live block state + random 5-6-char codes")


if __name__ == "__main__":
    main()
