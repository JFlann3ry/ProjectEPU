from __future__ import annotations

from time import time

from sqlalchemy.orm import Session

from app.models.rate_limit import RateLimitCounter


def allow(db: Session, key: str, limit: int, window_seconds: int) -> bool:
    """Return True if request is allowed under a fixed-window counter.

    Stores counters in the database so limits are shared across instances.
    If the DB write fails, the request is allowed to avoid breaking primary flows.
    """
    window = int(time()) // max(1, window_seconds)

    try:
        bucket = (
            db.query(RateLimitCounter)
            .with_for_update()
            .filter(RateLimitCounter.Key == key, RateLimitCounter.Window == window)
            .first()
        )
        if bucket is None:
            bucket = RateLimitCounter(Key=key, Window=window, Count=1)
            db.add(bucket)
            db.commit()
            return True

        bucket.Count = int(bucket.Count or 0) + 1
        db.commit()
        return bucket.Count <= int(limit)
    except Exception:
        db.rollback()
        # If rate limit storage fails, allow the request rather than blocking users
        return True
