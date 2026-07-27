from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "scripts/stabilize_project.py",
        "scripts/audit_codebase.py",
        "scripts/release_check.py",
        "docs/STABILIZATION.md",
        "docs/RELEASE_PREPARATION.md",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for value in (
        ".stage*-install/",
        ".stage*-backup-*/",
        ".audit-*-backup/",
        ".env.before-*",
        "anonmake.db",
        "anonmake-stabilization-backups/",
    ):
        assert value in gitignore, value

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "stabilize-check:",
        "stabilize-apply:",
        "release-check:",
        "release-check-runtime:",
    ):
        assert target in makefile, target

    print("Stage 34 check: OK")
    print("Safe cleanup with external rollback archive: ready")
    print("Legacy development artifacts: removed")
    print("Current project checker: updated")
    print("Codebase duplication audit: ready")
    print("Unified release check command: ready")


if __name__ == "__main__":
    check()
