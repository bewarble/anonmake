from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, (path, needle)


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
        'Command("menu")',
        'Command("help")',
        "await state.clear()",
        "texts.UNKNOWN_INPUT",
        "fallback_router",
    )
    require(
        "app/bot/handlers/start.py",
        "texts.WELCOME",
        "main_menu_for(message.from_user.id)",
        "personal_link_share_keyboard(link)",
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
        "MAIN_MENU",
        "/menu",
        "/cancel",
    )
    assert not list((ROOT / "migrations/versions").glob("*stage_58*"))
    print("Stage 58 check: OK")
    print("Bot main menu, help, /menu and unknown-input fallback are wired")
    print("Navigation commands can safely leave active FSM flows")
    print("No Stage 58 migration required")


if __name__ == "__main__":
    main()
