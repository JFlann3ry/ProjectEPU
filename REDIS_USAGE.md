# Redis usage and limits (ProjectEPU)

Last updated: 2025-10-03

This document describes where Redis is used in the app, what it controls, and the exact limits configured. Redis is optional; when not configured, the app falls back to in‑memory, per‑process counters which are not shared across instances.

## Configuration

- Env var: `REDIS_URL` (see `.env` / `.env.example`)
  - Format: `redis://[:password]@host:port/db`
  - Example: `redis://:password@127.0.0.1:6379/0`
- Code: `app/services/rate_limit.py` lazily initializes a client with `redis.Redis.from_url(REDIS_URL, decode_responses=True)`.
- If `REDIS_URL` is empty or Redis is unavailable, the code uses an in‑memory fallback.

## Usage overview

Redis is used for shared rate limiting across instances via a simple fixed‑window counter. Current Redis‑backed use cases:

1) Contact form submissions (/contact)
   - File: `app/api/support.py`
   - Gate: `rl_allow("contact:{client_ip}", limit, window_seconds)`
   - Settings:
     - `CONTACT_RATE_LIMIT_ATTEMPTS` (default 3)
     - `CONTACT_RATE_LIMIT_WINDOW_SECONDS` (default 60 seconds)
   - Behavior: On exceeding the limit, responds with HTTP 429 and re-renders the contact page with an error.

2) General rate limiter helper (available for other routes)
   - File: `app/services/rate_limit.py`
   - Function: `allow(key: str, limit: int, window_seconds: int) -> bool`
   - Implementation:
     - Fixed window: key is expanded to `"{key}:{current_window_index}"` where `current_window_index = floor(now / window_seconds)`.
     - Redis pipeline increments the counter and sets TTL to `window_seconds + 5`.
     - Returns True if `count <= limit`.
   - Fallback: If Redis is not configured or errors out, uses an in-memory deque per key with time-based trimming.

## Not currently Redis-backed (but rate limited elsewhere)

The following limits are enforced without Redis today; they are noted here for completeness and potential future migration to Redis:

- Login attempts
  - File: `app/services/auth.py`
  - Mechanism: In-memory deque `_login_attempts` keyed by identifier (e.g., IP/email pair depending on caller usage).
  - Settings:
    - `RATE_LIMIT_LOGIN_ATTEMPTS` (default 5)
    - `RATE_LIMIT_LOGIN_WINDOW_SECONDS` (default 900 seconds / 15 minutes)
  - Behavior: When the count within the window reaches the limit, further attempts are considered rate-limited.
  - Note: Per-process only. For multi-instance deployments, consider moving to `rate_limit.allow` (Redis) for shared enforcement.

- Billing: Email receipt sending
  - File: `app/api/billing.py` (`/billing/purchase/{purchase_id}/email-receipt`)
  - Mechanism: Database-backed check in `PaymentLog` to ensure max 1 email per user per rolling hour.

- Uploads: Guest message per-session throttle
  - File: `app/api/uploads.py`
  - Mechanism: Database count of `GuestMessage` in the last 10 minutes per (EventID, GuestSessionID). Allows up to 3 messages per 10 minutes.

## Keys and TTLs (Redis)

- Base key passed by caller, e.g., `contact:203.0.113.10`.
- Expanded key in Redis: `"{base_key}:{window}"` where `window = floor(now / window_seconds)`.
- On each call:
  - `INCR key`
  - `EXPIRE key` set to `window_seconds + 5` seconds
- Allowed when the post-increment count `<= limit`.

## Operational considerations

- Fallback behavior: If Redis is unavailable or `REDIS_URL` not set, the limiter falls back to per-process in-memory queues. With multiple app instances, limits won’t be shared across instances.
- Persistence: Redis is used as a short-lived counter store. No durable data is stored; keys expire automatically.
- Security: Do not expose your `REDIS_URL` (password/host) publicly. Use network policies/security groups.
- Monitoring: Consider adding Redis metrics (keyspace hits/misses, mem usage) and alerting on connection errors.

## Quick reference (defaults)

- Contact form: 3 requests per 60 seconds per client IP (Redis if configured).
- Login: 5 attempts per 15 minutes (in-memory per process).
- Billing receipt email: 1 per user per hour (DB-enforced).
- Upload guest messages: 3 per 10 minutes per guest session (DB-enforced).

## Future improvements

- Migrate login attempt limiting to Redis (using `rate_limit.allow`) for shared enforcement across instances.
- Add per-user and per-route granularity as needed.
- Consider sliding window or token bucket algorithm if smoother limiting is required.
