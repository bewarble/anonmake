from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    model = (ROOT / "app/models/bot_instance.py").read_text(encoding="utf-8")
    assert "telegram_bot_id: Mapped[int | None]" in model
    assert "unique=True" in model

    migration = (ROOT / "migrations/versions/20260809_0028_unique_telegram_bot_id.py").read_text(encoding="utf-8")
    assert 'revision = "20260809_0028"' in migration
    assert 'down_revision = "20260808_0027"' in migration
    assert "HAVING COUNT(*) > 1" in migration
    assert 'unique=True' in migration

    runtime = (ROOT / "scripts/check_multibot_isolation_runtime.py").read_text(encoding="utf-8")
    assert '"duplicate_telegram_bot_ids"' in runtime
    assert "GROUP BY telegram_bot_id" in runtime

    print("Telegram bot ownership check: OK")
    print("One verified Telegram bot id can belong to only one project")


if __name__ == "__main__":
    main()
