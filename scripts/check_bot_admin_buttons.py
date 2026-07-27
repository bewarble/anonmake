from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

keyboard = (
    ROOT / "app/bot/keyboards/main_menu.py"
).read_text(encoding="utf-8")

handler = (
    ROOT / "app/bot/handlers/admin_stage25_1.py"
).read_text(encoding="utf-8")

constants = (
    "ADMIN_STATISTICS",
    "ADMIN_BROADCAST",
    "ADMIN_PROFIT",
    "ADMIN_EXPORT",
    "ADMIN_SOURCES",
)

for constant in constants:
    assert constant in keyboard, f"{constant} отсутствует в клавиатуре"
    assert constant in handler, f"{constant} не подключён к обработчику"

assert 'F.text == "Статистика"' not in handler
assert 'F.text == "Прибыль"' not in handler
assert 'F.text == "Рассылка"' not in handler
assert 'F.text == "Выгрузка"' not in handler
assert 'F.text == "Рефералы"' not in handler

print("Telegram admin buttons check: OK")
print("📊 Статистика: ready")
print("📣 Рассылка: ready")
print("💰 Прибыль: ready")
print("📦 Выгрузка: ready")
print("🔗 Источники: ready")
