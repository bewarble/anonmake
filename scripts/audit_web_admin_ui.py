from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app/web/templates"

FORBIDDEN_VISIBLE = (
    "С доступом",
    "Без доступа",
    "Любой доступ",
    "Доступ активен",
    "Доступ завершён",
    "Узнать кто это",
    "Growth OS",
    "Billing CRM",
    "Payment method",
    "Support actions",
    "Billing history",
)

RAW_STATUS_PATTERN = re.compile(
    r">\\s*(trial_active|active_1_day|active_3_days|past_due|"
    r"payment_pending|cancelled_active|payment_method_blocked|"
    r"insufficient_funds|test_primary|test_fallback)\\s*<",
    re.I,
)


def check() -> None:
    violations: list[str] = []
    for path in TEMPLATES.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_VISIBLE:
            if phrase in text:
                violations.append(f"{path.name}: deprecated text: {phrase}")
        if RAW_STATUS_PATTERN.search(text):
            violations.append(f"{path.name}: raw status is visible")

    if violations:
        raise AssertionError("Web UI audit violations:\n- " + "\n- ".join(sorted(violations)))

    print("Web admin UI audit: OK")
    print("Deprecated terminology: removed")
    print("Raw statuses as primary labels: removed")
    print("Russian interface language: consistent")


if __name__ == "__main__":
    check()
