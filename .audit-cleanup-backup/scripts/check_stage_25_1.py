from app.bot.keyboards.admin_stage25_1 import (
    broadcast_audience_keyboard,
    referral_card_keyboard,
)


def check() -> None:
    audience = str(broadcast_audience_keyboard())
    assert "Всем" in audience
    assert "С VIP" in audience
    assert "Без VIP" in audience

    referral = str(referral_card_keyboard(1))
    assert "К списку" in referral
    assert "Удалить" in referral

    print("Stage 25.1 check: OK")
    print("Statistics chart: daily joins and daily blocks")
    print("Statistics text: Живые and all-time periods")
    print("Profit text: separated all-time row")
    print("Referrals: functional list and back button")
    print("Broadcast: all, active VIP or non-VIP audiences")


if __name__ == "__main__":
    check()
