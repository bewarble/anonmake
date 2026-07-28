from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_python_syntax() -> int:
    files = sorted((ROOT / "app").rglob("*.py"))
    files += sorted((ROOT / "scripts").rglob("*.py"))

    for path in files:
        ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )

    return len(files)


def check_template_references() -> int:
    templates_dir = ROOT / "app/web/templates"
    referenced: set[str] = set()

    pattern = re.compile(
        r"""(?:name\s*=\s*|TemplateResponse\(\s*)["']([^"']+\.html)["']"""
    )

    for path in (ROOT / "app/web").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        referenced.update(pattern.findall(text))

    missing = sorted(
        name
        for name in referenced
        if not (templates_dir / name).is_file()
    )
    assert not missing, f"Missing templates: {missing}"

    return len(referenced)


def check_telegram_html() -> int:
    files_checked = 0
    tags = ("<b>", "</b>", "<code>", "</code>", "<a href=")

    for path in (ROOT / "app/bot").rglob("*.py"):
        text = path.read_text(encoding="utf-8")

        if any(tag in text for tag in tags):
            assert (
                "parse_mode=" in text
                or "ParseMode.HTML" in text
                or 'parse_mode="HTML"' in text
            ), f"Telegram HTML without parse_mode: {path.relative_to(ROOT)}"

        files_checked += 1

    return files_checked


def compose_services() -> set[str]:
    services: set[str] = set()

    for filename in (
        "compose.yaml",
        "compose.backup.yaml",
        "compose.delivery.yaml",
        "compose.marketing.yaml",
    ):
        path = ROOT / filename
        if not path.is_file():
            continue

        text = path.read_text(encoding="utf-8")
        inside_services = False

        for line in text.splitlines():
            if line == "services:":
                inside_services = True
                continue

            if inside_services and line and not line.startswith(" "):
                inside_services = False

            if not inside_services:
                continue

            match = re.match(r"^  ([a-zA-Z0-9_-]+):\s*$", line)
            if match:
                services.add(match.group(1))

    return services


def check_compose_registry() -> set[str]:
    services = compose_services()

    required = {
        "db",
        "redis",
        "bot",
        "web",
        "worker",
        "delivery-worker",
        "broadcast-worker",
    }

    missing = sorted(required - services)
    assert not missing, f"Missing Compose services: {missing}"

    return services


def main() -> None:
    python_count = check_python_syntax()
    template_count = check_template_references()
    telegram_count = check_telegram_html()
    services = check_compose_registry()

    print("Final QA check: OK")
    print(f"Python syntax: verified ({python_count} files)")
    print(f"Telegram HTML parse modes: verified ({telegram_count} files)")
    print(f"Jinja template references: verified ({template_count} templates)")
    print(
        "Docker Compose service registry: verified "
        f"({len(services)} services)"
    )


if __name__ == "__main__":
    main()
