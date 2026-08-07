from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

STATIC_CHECKS = (
    "scripts.check_final_qa",
    "scripts.check_stage_38_1",
    "scripts.check_stage_38_2",
    "scripts.check_stage_38_3",
    "scripts.check_stage_38_4",
    "scripts.check_stage_39",
    "scripts.check_stage_40",
    "scripts.check_stage_41",
    "scripts.check_stage_42",
    "scripts.check_stage_43",
    "scripts.check_stage_44",
    "scripts.check_stage_45",
    "scripts.check_stage_46",
    "scripts.check_stage_47",
    "scripts.check_stage_48",
    "scripts.check_stage_49",
    "scripts.check_stage_50",
    "scripts.check_stage_51",
    "scripts.check_full_audit",
    "scripts.check_stage_36",
    "scripts.check_project",
    "scripts.check_stage_34",
    "scripts.check_stage_35",
    "scripts.audit_active_web_assets",
    "scripts.audit_codebase",
    "scripts.check_product_language",
    "scripts.audit_telegram_copy",
    "scripts.check_bot_admin_buttons",
    "scripts.audit_web_admin_ui",
    "scripts.audit_route_registry",
    "scripts.check_stage_33",
)

RUNTIME_CHECKS = (
    "scripts.check_dependencies",
    "scripts.check_migration_head",
    "scripts.check_web_admin_runtime",
    "scripts.check_stage_49_runtime",
)


def run_module(module: str) -> None:
    print()
    print("=" * 72)
    print("Running:", module)
    print("=" * 72)

    subprocess.run(
        [sys.executable, "-m", module],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="AnonMake release readiness checks")
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="run static and runtime checks",
    )
    parser.add_argument(
        "--runtime-only",
        action="store_true",
        help="run only checks requiring PostgreSQL, Redis and web runtime",
    )
    args = parser.parse_args()

    if not args.runtime_only:
        for module in STATIC_CHECKS:
            run_module(module)

    if args.runtime or args.runtime_only:
        for module in RUNTIME_CHECKS:
            run_module(module)

    if args.runtime_only:
        mode = "runtime only"
    elif args.runtime:
        mode = "static + runtime"
    else:
        mode = "static"

    print()
    print("Release check: OK")
    print("Mode:", mode)


if __name__ == "__main__":
    main()
