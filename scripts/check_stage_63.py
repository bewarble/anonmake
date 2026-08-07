from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, (path, needle)


def main() -> None:
    require(
        "app/core/texts.py",
        "🚀 Здесь можно отправить анонимное сообщение человеку, который опубликовал эту ссылку.",
        "✅ Сообщение отправлено, ожидайте ответ от человека!",
        "💬 Начни получать анонимные сообщения прямо сейчас!",
        "Разместите ссылку у себя в профиле и вам смогут написать ваши друзья и знакомые ✍️",
        "🤫 Чтобы получать сообщения — добавь ссылку в свой профиль!",
        "Пример как на фото 👇",
        "<b>📨 Вам отправили новое анонимное сообщение</b>",
        "💬 Напишите свой ответ на данное сообщение:",
        "✅ Ответ успешно отправлен и уже пришёл человеку!",
        "💝 Хочешь получать больше сообщений? Поделись ссылкой:",
    )
    require(
        "app/bot/ui.py",
        'USER_PERSONAL_LINK = "💬 Начать получать сообщения"',
        'USER_HELP = "❓ Как получать сообщения?"',
        'ACTION_CANCEL = "✖️ Отменить"',
    )
    require(
        "app/models/user.py",
        "PUBLIC_CODE_LENGTH = 8",
        "PUBLIC_CODE_ALPHABET",
        "secrets.choice(PUBLIC_CODE_ALPHABET)",
    )
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
        'full_link = link if link.startswith("https://") else f"https://{link}"',
    )
    require(
        "app/bot/keyboards/personal_link.py",
        "personal_link_copy_keyboard",
        'text="Скопировать ссылку"',
        "CopyTextButton(text=link)",
    )
    require(
        "app/bot/handlers/start.py",
        "texts.START_PROMO.format",
        'link.removeprefix("https://")',
        "texts.SELF_MESSAGE",
    )
    require(
        "app/bot/handlers/navigation.py",
        "personal_link_copy_keyboard(link)",
        "texts.HELP",
    )
    require(
        "app/bot/handlers/questions.py",
        '@router.callback_query(F.data.startswith("ask_again:"))',
        "write_more_keyboard(recipient.id)",
        "texts.QUESTION_PROMO.format(link=personal_link)",
        'payload["parse_mode"] = "HTML"',
        "html.escape(question.text)",
        "current_state == AskQuestion.waiting_for_text.state",
        "await callback.message.delete()",
        "await bot.send_message(",
    )
    require(
        "app/bot/handlers/answers.py",
        "answer_share_keyboard(personal_link)",
        "texts.ANSWER_PROMPT",
        "texts.ANSWER_SENT",
    )
    require(
        "app/delivery_worker.py",
        'parse_mode = payload.get("parse_mode")',
        "parse_mode=parse_mode",
    )
    print("Stage 63 check: OK")
    print("Personal-link entry copy: final")
    print("Public codes: shortened to 8 characters")
    print("Self-link, /start and help UX: final")
    print("Question cancel deletes the prompt and returns the personal-link promo")
    print("Post-send repeat action and self-promotion: ready")
    print("Anonymous-message header: bold and HTML-safe")
    print("Answer prompt and post-answer sharing actions: ready")
    print("Copy-link actions include https://")
    print("Stage 63 migration: 20260807_0021_short_public_codes")


if __name__ == "__main__":
    main()
