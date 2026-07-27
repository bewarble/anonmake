from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEXTS_FILE = ROOT / "app/core/texts.py"
HANDLERS_ROOT = ROOT / "app/bot/handlers"
KEYBOARDS_ROOT = ROOT / "app/bot/keyboards"

EXCLUDED_NAMES = {
    "recurrent_test.py",
}

USER_VISIBLE_METHODS = {
    "answer",
    "reply",
    "edit_text",
    "edit_caption",
    "send_message",
    "send_photo",
    "send_document",
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

ALLOWED_OFFER = "1 ₽ — 1 день доступа"


def iter_python_files(root: Path):
    if not root.exists():
        return

    for path in root.rglob("*.py"):
        if path.name in EXCLUDED_NAMES:
            continue
        if path.name.startswith("admin_"):
            continue
        yield path


def check_value(
    *,
    path: Path,
    line_no: int,
    value: str,
    violations: list[str],
) -> None:
    for name, pattern in FORBIDDEN.items():
        if pattern.search(value):
            violations.append(
                f"{path.relative_to(ROOT)}:{line_no}: {name}"
            )


def check_texts_file(violations: list[str]) -> None:
    source = TEXTS_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TEXTS_FILE))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            check_value(
                path=TEXTS_FILE,
                line_no=node.lineno,
                value=node.value,
                violations=violations,
            )


def method_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr

    if isinstance(call.func, ast.Name):
        return call.func.id

    return None


def direct_string_arguments(call: ast.Call):
    for argument in call.args:
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            yield argument

    for keyword in call.keywords:
        if isinstance(keyword.value, ast.Constant) and isinstance(
            keyword.value.value,
            str,
        ):
            yield keyword.value


def check_user_visible_calls(
    path: Path,
    violations: list[str],
) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if method_name(node) not in USER_VISIBLE_METHODS:
            continue

        for string_node in direct_string_arguments(node):
            check_value(
                path=path,
                line_no=string_node.lineno,
                value=string_node.value,
                violations=violations,
            )


def check_keyboard_labels(
    path: Path,
    violations: list[str],
) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        for keyword in node.keywords:
            if keyword.arg != "text":
                continue

            value = keyword.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                check_value(
                    path=path,
                    line_no=value.lineno,
                    value=value.value,
                    violations=violations,
                )


def check() -> None:
    violations: list[str] = []

    check_texts_file(violations)

    for path in iter_python_files(HANDLERS_ROOT):
        check_user_visible_calls(path, violations)

    for path in iter_python_files(KEYBOARDS_ROOT):
        check_keyboard_labels(path, violations)

    texts = TEXTS_FILE.read_text(encoding="utf-8")
    if ALLOWED_OFFER not in texts:
        violations.append(
            "app/core/texts.py: public offer missing"
        )

    if violations:
        raise AssertionError(
            "Product language violations:\n- "
            + "\n- ".join(sorted(set(violations)))
        )

    print("Product language audit: OK")
    print("Public offer: 1 ₽ / 1 day")
    print("Renewal amounts and billing internals: hidden")
    print("Access dates: hidden")


if __name__ == "__main__":
    check()
