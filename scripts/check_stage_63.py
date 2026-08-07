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
        "<b>📨 Вам отправили новое анонимное сообщение</b>",
        "💬 Напишите свой ответ на данное сообщение:",
        "✅ Ответ успешно отправлен и уже пришёл человеку!",
        "💝 Хочешь получать больше сообщений? Поделись ссылкой:",
    )
    require(
        "app/bot/keyboards/questions.py",
        "CopyTextButton",
        'text="✍️ Написать ещё"',
        'text="🔗 Скопировать ссылку"',
        'text="📤 Выложить в каналы / чаты"',
        'callback_data=f"ask_again:{recipient_id}"',
    )
    require(
        "app/bot/handlers/questions.py",
        '@router.callback_query(F.data.startswith("ask_again:"))',
        "write_more_keyboard(recipient.id)",
        "texts.QUESTION_PROMO.format(link=personal_link)",
        'payload["parse_mode"] = "HTML"',
        "html.escape(question.text)",
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
    print("Post-send repeat action and self-promotion: ready")
    print("Anonymous-message header: bold and HTML-safe")
    print("Answer prompt and post-answer sharing actions: ready")
    print("No Stage 63 migration required")


if __name__ == "__main__":
    main()
