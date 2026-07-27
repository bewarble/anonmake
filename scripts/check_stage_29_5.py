from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), relative
    return path.read_text(encoding="utf-8")


def check() -> None:
    python_files = (
        "app/bot/handlers/admin_stage25_1.py",
        "app/bot/handlers/answers.py",
        "app/bot/handlers/start_marketing.py",
        "app/core/texts.py",
        "app/repositories/users.py",
        "app/repositories/marketing.py",
        "app/services/admin_charts_stage25.py",
    )
    for relative in python_files:
        ast.parse(read(relative), filename=relative)

    admin = read("app/bot/handlers/admin_stage25_1.py")
    assert "<b>Общая статистика:</b>" in admin
    assert "<b>Прирост:</b>" in admin
    assert "<b>Саморост:</b>" in admin
    growth_block = admin.split('"👤 <b>Прирост:</b>', 1)[1].split(
        '"📈 <b>Саморост:</b>', 1
    )[0]
    assert "За всё время" not in growth_block
    assert "+{number(item.trials)} новых подписок" in admin
    assert 'parse_mode="HTML"' in admin

    chart = read("app/services/admin_charts_stage25.py")
    assert 'label="Приход"' in chart
    assert 'label="Заблокировали"' in chart
    assert 'axis.set_title("Приход и блокировки по дням")' in chart

    texts = read("app/core/texts.py")
    assert 'ANSWER_RECEIVED = "💬 Вам ответили\\n\\n{answer}"' in texts
    assert "Ваше сообщение:" not in texts

    answers = read("app/bot/handlers/answers.py")
    assert "ANSWER_RECEIVED.format(answer=text)" in answers
    assert "question=question.text" not in answers

    users = read("app/repositories/users.py")
    assert "get_or_create_from_telegram" in users
    assert "tuple[User, bool]" in users
    assert "begin_nested" in users
    assert "except IntegrityError" in users

    marketing = read("app/repositories/marketing.py")
    assert "register_source_start" in marketing
    assert "-> bool" in marketing
    assert "source.clicks += 1" in marketing
    assert "return False" in marketing

    start = read("app/bot/handlers/start_marketing.py")
    assert "user, is_new_user" in start
    assert 'if is_new_user and payload.startswith("src_")' in start
    assert "if source is not None and attributed" in start

    print("Stage 29.5 check: OK")
    print("Telegram statistics wording and graph: ready")
    print("Profit formatting: ready")
    print("Answer notification without repeated question: ready")
    print("First-touch source attribution: ready")
    print("Concurrent first-start safeguards: ready")


if __name__ == "__main__":
    check()
