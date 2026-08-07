from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_CANDIDATES = ("origin/stage-38-multibot", "stage-38-multibot")
STAGE57_CANDIDATES = ("origin/stage-57-release-audit", "stage-57-release-audit")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def resolve_ref(candidates: tuple[str, ...], label: str) -> str:
    for candidate in candidates:
        if run("git", "rev-parse", "--verify", candidate).returncode == 0:
            return candidate
    raise AssertionError(f"{label} ref is unavailable; run git fetch origin")


def main() -> None:
    base = resolve_ref(BASE_CANDIDATES, "stage-38-multibot")
    stage57 = resolve_ref(STAGE57_CANDIDATES, "stage-57-release-audit")

    ancestry = run("git", "merge-base", "--is-ancestor", base, stage57)
    assert ancestry.returncode == 0, "stage-57-release-audit must descend from stage-38-multibot"

    release_ancestry = run("git", "merge-base", "--is-ancestor", stage57, "HEAD")
    assert release_ancestry.returncode == 0, "release branch must be a descendant of stage-57-release-audit"

    # Stage 57 owns only the Stage 38 -> Stage 57 release window. Later stages may
    # legitimately introduce migrations, so auditing all the way to HEAD would make
    # this historical checker fail for unrelated future work.
    changed_migrations = run(
        "git", "diff", "--name-only", f"{base}...{stage57}", "--", "migrations/versions"
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
    print("stage-38-multibot -> stage-57-release-audit ancestry: verified")
    print("No migration changes detected inside the Stage 38 through Stage 57 window")
    print("Later-stage migrations do not invalidate the historical Stage 57 audit")
    print("Stage 50-56 checkers, docs and active UX assets are present")


if __name__ == "__main__":
    main()
