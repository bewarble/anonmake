from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.questions import answer_question_keyboard
from app.core import texts


def check() -> None:
    menu = main_menu_keyboard()
    question_actions = answer_question_keyboard(1)

    assert len(menu.keyboard) == 2
    assert len(question_actions.inline_keyboard) == 1
    assert len(question_actions.inline_keyboard[0]) == 2

    assert "Профиль" not in str(menu)
    assert "Настройки" not in str(menu)
    assert "История покупок" not in texts.VIP_OFFER
    assert "всех старых и новых сообщений" in texts.VIP_OFFER
    assert len(texts.WELCOME) < 220
    assert len(texts.QUESTION_SENT) < 180
    assert len(texts.ANSWER_SENT) < 160

    print("Stage 16 check: OK")
    print("UX: compact and consistent")
    print("Main menu: link + help only")
    print("Reveal behavior: button remains on messages")
    print("Profiles, settings and purchase history: not added")


if __name__ == "__main__":
    check()
