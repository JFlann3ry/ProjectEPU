"""
Preflight runner: Ruff lint + unit tests + Playwright live e2e.

Windows-safe (no inline -c quoting). Use your venv's Python to run.
"""

from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str], title: str) -> int:
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)
    return subprocess.call(cmd)


def main() -> int:
    rc_lint = run([sys.executable, "-m", "ruff", "check", "."], title="Ruff lint")

    # Exclude e2e when running unit/integration to avoid running Playwright twice
    rc_unit = run(
        [sys.executable, "-m", "pytest", "-q", "-k", "not e2e"],
        title="Pytest (unit/integration, excluding e2e)",
    )

    # Focused Playwright test for Live HUD focus/keyboard behavior
    rc_play = run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/e2e/test_live_hud_focus.py",
            "-k",
            "live_hud_tab_order",
        ],
        title="Playwright: Live HUD focus test",
    )

    # Overall exit code
    return 0 if rc_lint == 0 and rc_unit == 0 and rc_play == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
