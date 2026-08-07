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
        "USER_PERSONAL_LINK",
        "USER_HELP",
    )
    require(
        "app/bot/keyboards/main_menu.py",
        "USER_HELP",
        "KeyboardButton(text=USER_PERSONAL_LINK)",
        "KeyboardButton(text=USER_HELP)",
    )
    require(
        "app/bot/keyboards/personal_link.py",
        'SHARE_TEXT = "Отправь мне анонимное сообщение 👉 {link}"',
        'short_link = link.removeprefix("https://")',
        'encoded_text = quote(share_text, safe="")',
        'text="Поделиться ссылкой"',
        '"https://t.me/share/url/?"',
        'f"url=%20&text={encoded_text}"',
    )
    reject(
        "app/bot/keyboards/personal_link.py",
        "tg://msg_url",
        '"url": link',
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
        "FSMContext",
        "await state.clear()",
    )
    reject(
        "app/bot/handlers/subscriptions.py",
        "StateFilter(None)",
    )
    require(
        "app/bot/handlers/__init__.py",
        "navigation_router",
        "navigation_fallback_router",
        "router.include_router(navigation_fallback_router)",
    )
    require(
        "app/managed_bots.py",
        "dispatcher.include_router(build_router())",
    )
    require(
        "Makefile",
        "docker-up:",
        "$(COMPOSE) up -d --build",
        "restart bot bot-two bot-three bot-four managed-bots",
    )
    reject(
        "Makefile",
        "docker-up-multibot",
        "--profile multibot",
    )
    reject(
        "compose.yaml",
        'profiles: ["multibot"]',
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
    print("Share action matches the Telegram share URL flow used by the reference implementation")
    print("Shared router is used by managed bot instances")
    print("Single docker-up path rebuilds all bot services")
    print("Help and unknown-input guidance are button-driven without command mentions")
    print("/cancel remains reserved for subscription auto-renew cancellation in every FSM state")
    print("No Stage 58 migration required")


if __name__ == "__main__":
    main()
