from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class CleanupItem:
    path: Path
    reason: str


def discover() -> list[CleanupItem]:
    items: dict[Path, CleanupItem] = {}

    patterns = (
        (".stage*-install", "legacy stage installer directory"),
        (".stage*-backup-*", "legacy stage backup directory"),
        (".audit-*-backup", "legacy audit backup directory"),
        ("*.bak-before-*", "temporary manual backup"),
        (".env.before-*", "temporary environment backup"),
        ("anonmake-stage-*.zip", "release artifact stored in repository"),
        ("anonmake-stage-*.zip.sha256", "release checksum stored in repository"),
    )
    for pattern, reason in patterns:
        for path in ROOT.glob(pattern):
            items[path] = CleanupItem(path, reason)

    exact = (
        ("anonmake.db", "local SQLite database; production uses PostgreSQL"),
        ("AUDIT_REPORT.md", "historical generated audit report"),
        ("REAUDIT_REPORT.md", "historical generated audit report"),
    )
    for name, reason in exact:
        path = ROOT / name
        if path.exists():
            items[path] = CleanupItem(path, reason)

    for path in ROOT.rglob("__pycache__"):
        items[path] = CleanupItem(path, "Python bytecode cache")
    for pattern in ("*.pyc", "*.pyo"):
        for path in ROOT.rglob(pattern):
            items[path] = CleanupItem(path, "Python bytecode file")

    # Never touch repository metadata, runtime data, or source-controlled examples.
    safe = []
    for item in sorted(items.values(), key=lambda value: str(value.path)):
        if ".git" in item.path.parts:
            continue
        if item.path == ROOT:
            continue
        safe.append(item)
    return safe


def create_archive(items: list[CleanupItem], output_dir: Path) -> Path | None:
    if not items:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = output_dir / f"anonmake-stabilization-backup-{timestamp}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as archive:
        for item in items:
            if not item.path.exists():
                continue
            archive.add(
                item.path,
                arcname=item.path.relative_to(ROOT),
                recursive=True,
            )
    return archive_path


def remove_item(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find and safely remove legacy AnonMake development artifacts."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="create an external backup archive and remove discovered artifacts",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=ROOT.parent / "anonmake-stabilization-backups",
        help="directory outside the repository for the rollback archive",
    )
    args = parser.parse_args()

    items = discover()
    if not items:
        print("Stabilization cleanup: nothing to remove")
        return

    print("Stabilization cleanup plan:")
    for item in items:
        print(f"- {item.path.relative_to(ROOT)} — {item.reason}")

    if not args.apply:
        print()
        print("Dry run only. Re-run with --apply to archive and remove these files.")
        return

    archive = create_archive(items, args.backup_dir)
    if archive is None:
        print("Nothing was archived.")
        return

    for item in items:
        remove_item(item.path)

    print()
    print("Stabilization cleanup: complete")
    print("Rollback archive:", archive)


if __name__ == "__main__":
    main()
