"""Cleanup completed export jobs and associated ZIP files in batches."""

from __future__ import annotations

import argparse

from app.jobs.maintenance import cleanup_completed_exports
from db import get_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup completed export jobs")
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=1_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_gen = get_db()
    db = next(db_gen)
    try:
        result = cleanup_completed_exports(
            db,
            retention_days=int(args.retention_days),
            batch_size=int(args.batch_size),
        )
        print(
            "retention_days={retention_days} batch_size={batch_size} batches={batches} "
            "deleted_rows={deleted_rows} deleted_files={deleted_files} "
            "missing_files={missing_files} cutoff={cutoff}".format(**result)
        )
        return 0
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
