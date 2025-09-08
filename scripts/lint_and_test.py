"""
Run Ruff lint and Pytest in sequence with clear exit code.

This avoids quoting issues seen with Python -c on Windows PowerShell.
Usage: run with your venv's python.
"""

from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def main() -> int:
    rc_lint = run([sys.executable, "-m", "ruff", "check", "."])
    rc_test = run([sys.executable, "-m", "pytest", "-q"])
    # Return non-zero if either failed
    return 0 if rc_lint == 0 and rc_test == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
