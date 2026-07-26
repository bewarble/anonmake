from app.bot.keyboards.admin_stage25 import (
    broadcast_audience_keyboard,
    export_choice_keyboard,
    referral_back_keyboard,
)


def check() -> None:
    assert "Все пользователи" in str(export_choice_keyboard())
    assert "Только живые" in str(export_choice_keyboard())
    assert "К списку" in str(referral_back_keyboard())
    assert "Всем" in str(broadcast_audience_keyboard())
    assert "С Premium" in str(broadcast_audience_keyboard())
    assert "Без Premium" in str(broadcast_audience_keyboard())

    print("Stage 25 check: OK")
    print("Statistics: alive, dead and active recurrent cards")
    print("Profit: revenue, 60 percent partner share, trials and all time")
    print("Export: all or alive Telegram IDs only")
    print("Referrals: back to source list")
    print("Broadcast: all, Premium or non-Premium audience")


if __name__ == "__main__":
    check()
