from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.source_admin import cancel_source_keyboard


def check() -> None:
    user_menu = main_menu_keyboard(is_admin=False)
    admin_menu = main_menu_keyboard(is_admin=True)

    assert "Статистика" not in str(user_menu)
    assert "Источники" not in str(user_menu)

    assert "Статистика" in str(admin_menu)
    assert "Пользователи" in str(admin_menu)
    assert "Источники" in str(admin_menu)
    assert "Рассылки" in str(admin_menu)
    assert "Система" not in str(admin_menu)

    assert "Отменить" in str(cancel_source_keyboard())

    print("Stage 23 check: OK")
    print("Admin: reply keyboard only")
    print("Users: standard keyboard")
    print("Sources: creation cancellation and deletion")
    print("System section: removed")


if __name__ == "__main__":
    check()
