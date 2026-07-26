from __future__ import annotations

from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
BACKUP_ROOT = ROOT / ".stage-backups" / "stage-3"

if not (ROOT / ".git").exists():
    print("ERROR: run from the anonmake repository root.", file=sys.stderr)
    raise SystemExit(1)

if not BACKUP_ROOT.exists():
    print("ERROR: Stage 3 backup was not found.", file=sys.stderr)
    raise SystemExit(1)

manifest = BACKUP_ROOT / "manifest.txt"
if not manifest.exists():
    print("ERROR: backup manifest is missing.", file=sys.stderr)
    raise SystemExit(1)

for line in manifest.read_text(encoding="utf-8").splitlines():
    action, relative_text = line.split("\t", maxsplit=1)
    relative = Path(relative_text)
    target = ROOT / relative
    backup = BACKUP_ROOT / "files" / relative

    if action == "RESTORE":
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
        print(f"Restored: {relative}")
    elif action == "REMOVE" and target.exists():
        target.unlink()
        print(f"Removed: {relative}")

print("Stage 3 files rolled back.")
print("The SQLite schema is not downgraded; questions/answers tables may remain locally.")
