"""Purge PaymentLog rows older than a retention window in batches."""

from __future__ import annotations

import argparse

from app.jobs.maintenance import purge_old_payment_logs
from db import get_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purge old PaymentLog rows")
    parser.add_argument("--retention-days", type=int, default=90)
    parser.add_argument("--batch-size", type=int, default=10_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_gen = get_db()
    db = next(db_gen)
    try:
        result = purge_old_payment_logs(
            db,
            retention_days=int(args.retention_days),
            batch_size=int(args.batch_size),
        )
        print(
            "retention_days={retention_days} batch_size={batch_size} batches={batches} "
            "deleted_rows={deleted_rows} cutoff={cutoff}".format(**result)
        )
        return 0
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
