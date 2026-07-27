from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def python_files() -> list[Path]:
    return sorted((ROOT / "app").rglob("*.py")) + sorted(
        (ROOT / "scripts").rglob("*.py")
    )


def duplicate_top_level_functions() -> list[str]:
    found: Counter[tuple[str, str]] = Counter()
    locations: dict[tuple[str, str], list[str]] = {}

    for path in python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module = ".".join(path.relative_to(ROOT).with_suffix("").parts)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                key = (module, node.name)
                found[key] += 1
                locations.setdefault(key, []).append(f"{path}:{node.lineno}")

    return [
        f"{module}.{name}: {', '.join(locations[(module, name)])}"
        for (module, name), count in found.items()
        if count > 1
    ]


def stage_named_runtime_files() -> list[str]:
    paths = []
    for root in (ROOT / "app").rglob("*stage*"):
        if root.is_file() and root.suffix in {".py", ".html", ".css", ".js"}:
            paths.append(str(root.relative_to(ROOT)))
    return sorted(paths)


def main() -> None:
    duplicates = duplicate_top_level_functions()
    stage_files = stage_named_runtime_files()

    print("Codebase audit")
    print("Python files:", len(python_files()))
    print("Duplicate top-level functions:", len(duplicates))
    for item in duplicates:
        print("-", item)

    print("Stage-named runtime files:", len(stage_files))
    for item in stage_files:
        print("-", item)

    # Duplicate functions inside one module are a correctness problem.
    if duplicates:
        raise AssertionError("Duplicate top-level function definitions detected")

    print("Codebase audit: OK")
    print("Stage-named files are reported for the next visual refactor, not deleted.")


if __name__ == "__main__":
    main()
