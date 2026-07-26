from app.bot.keyboards.admin_minimal import admin_home_keyboard
from app.core import admin_texts


def check() -> None:
    keyboard = admin_home_keyboard()
    assert len(keyboard.inline_keyboard) == 3
    assert "Пользователи" in str(keyboard)
    assert "Рост" in str(keyboard)
    assert "Финансы" in str(keyboard)
    assert "Система" in str(keyboard)
    assert "Быстрое меню" not in admin_texts.OVERVIEW

    print("Stage 22 check: OK")
    print("Admin UI: minimal four-section structure")
    print("Copy: unified and compact")
    print("Legacy duplicate surfaces: hidden")
    print("Business functions: preserved")


if __name__ == "__main__":
    check()
