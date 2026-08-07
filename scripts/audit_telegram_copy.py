from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ROOT / "app/bot/handlers",
    ROOT / "app/bot/keyboards",
    ROOT / "app/core/texts.py",
    ROOT / "app/core/admin_texts.py",
)

DEPRECATED = (
    "✖️ Отмена",
    "⭐ С доступом",
    "Без доступа",
    "⭐ Доступ",
    "Доступ открыт",
    "📣 Рефералы",
    "Узнать кто это",
)


def python_strings(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value


def check() -> None:
    problems = []
    counts = Counter()

    for target in TARGETS:
        paths = [target] if target.is_file() else target.rglob("*.py")
        for path in paths:
            for line, value in python_strings(path):
                for phrase in DEPRECATED:
                    if phrase in value:
                        problems.append(
                            f"{path.relative_to(ROOT)}:{line}: {phrase}"
                        )
                if value and value[0] in "✅⚠️❌ℹ️💌👤⭐🔗✍️⚙️📊📣💰📦":
                    counts[value[0]] += 1

    if problems:
        raise AssertionError(
            "Telegram copy audit violations:\n- "
            + "\n- ".join(sorted(problems))
        )

    print("Telegram copy audit: OK")
    print("Semantic emoji usage:", dict(sorted(counts.items())))


if __name__ == "__main__":
    check()
