from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_ROOTS = (
    ROOT / "app" / "core" / "texts.py",
    ROOT / "app" / "bot" / "handlers",
    ROOT / "app" / "bot" / "keyboards",
)

EXCLUDED_NAMES = {
    "recurrent_test.py",
    "admin.py",
    "admin_stage25.py",
    "admin_stage25_1.py",
}

FORBIDDEN = {
    "renewal_amounts": re.compile(r"\b(?:99|299)\s*₽", re.I),
    "billing_internals": re.compile(
        r"\b(?:MIT|fallback|primary|binding)\b",
        re.I,
    ),
    "technical_errors": re.compile(
        r"\b(?:AMOUNT_EXCEED|HTTP_\d{3}|transaction_id)\b",
        re.I,
    ),
    "access_dates": re.compile(
        r"(?:Доступ до|Следующее списание)",
        re.I,
    ),
}

ALLOWED_OFFER = "1 ₽ — 1 день VIP статуса"

ALLOWED_CONSENT_FRAGMENTS = (
    "Стоимость пробной VIP подписки — 1 ₽ за 1 день VIP статуса",
    "автоматической пролонгацией 299 ₽ каждые 3 дня",
    "частичное списание 99 ₽ за 1 день VIP статуса",
    "условиями пользования",
)


def iter_public_files():
    for root in PUBLIC_ROOTS:
        if root.is_file():
            yield root
            continue

        for path in root.rglob("*.py"):
            if path.name in EXCLUDED_NAMES:
                continue
            if path.name.startswith("admin_"):
                continue
            yield path


def string_literals(path: Path):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value


def is_allowed_consent_text(path: Path, value: str) -> bool:
    if path.relative_to(ROOT).as_posix() != "app/core/texts.py":
        return False

    return any(
        fragment in value
        for fragment in ALLOWED_CONSENT_FRAGMENTS
    )


def check() -> None:
    violations: list[str] = []

    for path in iter_public_files():
        for line_no, value in string_literals(path):
            for name, pattern in FORBIDDEN.items():
                if not pattern.search(value):
                    continue

                if (
                    name == "renewal_amounts"
                    and is_allowed_consent_text(path, value)
                ):
                    continue

                violations.append(
                    f"{path.relative_to(ROOT)}:{line_no}: {name}"
                )

    texts_path = ROOT / "app/core/texts.py"
    texts = texts_path.read_text(encoding="utf-8")

    if ALLOWED_OFFER not in texts:
        violations.append(
            "app/core/texts.py: public offer missing"
        )

    for fragment in ALLOWED_CONSENT_FRAGMENTS:
        if fragment not in texts:
            violations.append(
                f"app/core/texts.py: consent fragment missing: {fragment}"
            )

    if violations:
        raise AssertionError(
            "Product language violations:\n- "
            + "\n- ".join(sorted(set(violations)))
        )

    print("Product language audit: OK")
    print("Public offer: 1 ₽ / 1 day of VIP status")
    print("Renewal amounts: allowed only in payment consent")
    print("Billing internals and technical errors: hidden")
    print("Access dates: hidden")


if __name__ == "__main__":
    check()
