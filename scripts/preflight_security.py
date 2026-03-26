"""Security preflight for critical production settings.

Usage examples:
  python scripts/preflight_security.py --mode auto
  python scripts/preflight_security.py --mode production
  python scripts/preflight_security.py --mode development --strict
"""

from __future__ import annotations

import argparse
import os

from app.core.security_preflight import format_report, run_security_preflight
from app.core.settings import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run security preflight checks")
    parser.add_argument(
        "--mode",
        choices=("auto", "production", "development"),
        default="auto",
        help="How to evaluate production checks",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when any critical setting is unsafe even in development mode",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exit_code, production_mode, problems = run_security_preflight(
        settings,
        mode=str(args.mode),
        strict=bool(args.strict),
        env=str(os.getenv("ENV", "")),
        app_env=str(os.getenv("APP_ENV", "")),
    )
    print(
        format_report(
            production_mode=production_mode,
            strict=bool(args.strict),
            problems=problems,
        )
    )
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
