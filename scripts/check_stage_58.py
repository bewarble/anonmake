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
        "async def show_home",
        "texts.PERSONAL_LINK",
        "main_menu_for(message.from_user.id if message.from_user else None)",
        "personal_link_share_keyboard(link)",
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
        "PERSONAL_LINK_SHARE",
        "HELP",
    )
    reject(
        "app/core/texts.py",
        "/menu",
        "/help",
        "отменить текущее действие",
    )
    assert not list((ROOT / "migrations/versions").glob("*stage_58*"))
    print("Stage 58 check: OK")
    print("/start is the single home command and exposes the personal link with the reply keyboard")
    print("Help and unknown-input guidance are button-driven without command mentions")
    print("/cancel remains reserved for subscription auto-renew cancellation")
    print("No Stage 58 migration required")


if __name__ == "__main__":
    main()
