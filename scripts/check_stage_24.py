from app.bot.keyboards.main_menu import main_menu_keyboard


def check() -> None:
    user_menu = main_menu_keyboard(is_admin=False)
    admin_menu = main_menu_keyboard(is_admin=True)

    assert "Моя ссылка" in str(user_menu)
    assert "Как это работает" in str(user_menu)

    assert "Моя ссылка" not in str(admin_menu)
    assert "Как это работает" not in str(admin_menu)
    assert "Статистика" in str(admin_menu)
    assert "Рассылка" in str(admin_menu)
    assert "Прибыль" in str(admin_menu)
    assert "Выгрузка" in str(admin_menu)
    assert "Рефералы" in str(admin_menu)

    print("Stage 24 check: OK")
    print("Admin keyboard: statistics, broadcast, profit, export, referrals")
    print("Basic user buttons: removed from admin keyboard")
    print("User keyboard: unchanged")


if __name__ == "__main__":
    check()
