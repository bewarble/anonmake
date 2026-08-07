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
        "app/bot/ui.py",
        'USER_PERSONAL_LINK = "🔗 Моя ссылка"',
        'USER_HELP = "❓ Помощь"',
    )
    require(
        "app/bot/keyboards/main_menu.py",
        "USER_HELP",
        "KeyboardButton(text=USER_PERSONAL_LINK)",
        "KeyboardButton(text=USER_HELP)",
    )
    require(
        "app/bot/keyboards/personal_link.py",
        'SHARE_TEXT = "Отправь мне анонимное сообщение 👉"',
        'encoded_url = quote(link, safe="")',
        'encoded_text = quote(SHARE_TEXT, safe="")',
        'text="Поделиться ссылкой"',
        '"tg://msg_url?"',
        'f"url={encoded_url}&text={encoded_text}"',
    )
    reject(
        "app/bot/keyboards/personal_link.py",
        "https://t.me/share/url?text=",
        "urlencode(",
    )
    require(
        "app/bot/handlers/navigation.py",
        "F.text == USER_HELP",
        "texts.UNKNOWN_INPUT",
        "fallback_router",
    )
    reject(
        "app/bot/handlers/navigation.py",
        'Command("menu")',
        'Command("help")',
    )
    require(
        "app/bot/handlers/start.py",
        "CommandStart()",
        "async def show_personal_link_message",
        "texts.PERSONAL_LINK",
        "personal_link_share_keyboard(link)",
        "reply_markup=main_menu_for(message.from_user.id)",
    )
    reject(
        "app/bot/handlers/start.py",
        "texts.PERSONAL_LINK_SHARE",
    )
    require(
        "app/bot/handlers/questions.py",
        'callback.data == "cancel"',
        "AskQuestion.waiting_for_text",
    )
    reject(
        "app/bot/handlers/questions.py",
        'Command("cancel")',
    )
    require(
        "app/bot/handlers/subscriptions.py",
        'Command("cancel")',
        "StateFilter(None)",
    )
    require(
        "app/bot/handlers/__init__.py",
        "navigation_router",
        "navigation_fallback_router",
        "router.include_router(navigation_fallback_router)",
    )
    require(
        "app/core/texts.py",
        "UNKNOWN_INPUT",
        "HELP",
    )
    reject(
        "app/core/texts.py",
        "/menu",
        "/help",
        "отменить текущее действие",
        "PERSONAL_LINK_SHARE",
    )
    assert not list((ROOT / "migrations/versions").glob("*stage_58*"))
    print("Stage 58 check: OK")
    print("/start installs the reply keyboard and personal-link messages own their inline share button")
    print("Share action uses Telegram's native msg_url deep link without browser fallback")
    print("Help and unknown-input guidance are button-driven without command mentions")
    print("/cancel remains reserved for subscription auto-renew cancellation")
    print("No Stage 58 migration required")


if __name__ == "__main__":
    main()
