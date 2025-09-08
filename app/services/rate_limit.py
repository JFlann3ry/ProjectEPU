from __future__ import annotations

from collections import defaultdict, deque
from time import time

from app.core.settings import settings

# Try to create a Redis client lazily; fallback to in-memory if unavailable
_redis = None
try:
    import redis  # type: ignore

    if settings.REDIS_URL:
        _redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    _redis = None

_inmem_buckets = defaultdict(lambda: deque())


def allow(key: str, limit: int, window_seconds: int) -> bool:
    """Return True if request is allowed under a token-bucket limit, else False.
    Uses Redis if configured, otherwise falls back to in-memory per-process buckets.
    """
    if _redis is not None:
        try:
            # Use a fixed window counter (simple and sufficient here)
            now = int(time())
            window = now // max(1, window_seconds)
            field = f"{key}:{window}"
            pipe = _redis.pipeline()
            pipe.incr(field, 1)
            pipe.expire(field, window_seconds + 5)
            count, _ = pipe.execute()
            return int(count) <= int(limit)
        except Exception:
            pass
    # Fallback in-memory
    q = _inmem_buckets[key]
    nowf = time()
    while q and q[0] < nowf - window_seconds:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(nowf)
    return True
