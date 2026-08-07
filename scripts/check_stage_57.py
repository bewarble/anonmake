from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_CANDIDATES = ("origin/stage-38-multibot", "stage-38-multibot")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def resolve_base() -> str:
    for candidate in BASE_CANDIDATES:
        if run("git", "rev-parse", "--verify", candidate).returncode == 0:
            return candidate
    raise AssertionError("stage-38-multibot ref is unavailable; run git fetch origin")


def main() -> None:
    base = resolve_base()

    ancestry = run("git", "merge-base", "--is-ancestor", base, "HEAD")
    assert ancestry.returncode == 0, "release branch must be a descendant of stage-38-multibot"

    changed_migrations = run(
        "git", "diff", "--name-only", f"{base}...HEAD", "--", "migrations/versions"
    )
    assert changed_migrations.returncode == 0, changed_migrations.stderr
    assert not changed_migrations.stdout.strip(), changed_migrations.stdout

    for stage in range(50, 57):
        assert (ROOT / f"scripts/check_stage_{stage}.py").is_file(), stage
        docs = list((ROOT / "docs").glob(f"STAGE_{stage}_*.md"))
        assert docs, f"Stage {stage} documentation is missing"

    required_assets = [
        "admin-stage50.css",
        "admin-stage51.css", "admin-stage51.js",
        "admin-stage52.css", "admin-stage52.js",
        "admin-stage53.css", "admin-stage53.js",
        "admin-stage54.css", "admin-stage54.js",
        "admin-stage55.css",
        "admin-stage56.css",
    ]
    for asset in required_assets:
        assert (ROOT / "app/web/static" / asset).is_file(), asset

    print("Stage 57 release audit: OK")
    print("stage-38-multibot is an ancestor of the release branch")
    print("No migration changes detected from Stage 38 through Stage 57")
    print("Stage 50-56 checkers, docs and active UX assets are present")


if __name__ == "__main__":
    main()
