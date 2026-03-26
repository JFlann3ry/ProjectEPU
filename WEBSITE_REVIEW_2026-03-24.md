# Website Review Backlog (2026-03-24)

Fresh full-site audit backlog for ProjectEPU.
This list focuses on currently open, verified items only (not repeating work already completed on 2026-03-23 unless a risk remains).

How to use
- Work top-to-bottom by priority: `P0` then `P1` then `P2`.
- Keep each PR focused on one to three items.
- Mark items done with a short note and PR link.

Legend
- `P0` = critical risk / high-impact reliability
- `P1` = meaningful product and quality improvements
- `P2` = optimization and polish
- Effort: `S` (<=1 day), `M` (2-4 days), `L` (5+ days)

## P0 - Security and Payment Reliability

- [x] `P0-01` Replace raw SQL execution in Stripe webhook with safe SQLAlchemy text. (`S`)
  - Why: webhook currently executes a raw SQL string directly and swallows errors.
  - Evidence: `app/api/billing.py` (`db.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")` inside a broad `try/except`).
  - Done when: isolation statement uses `sqlalchemy.text(...)`, DB support is checked explicitly, and unsupported backends are logged at debug level rather than silently ignored.
  - Completed: 2026-03-24 (`app/api/billing.py`, `tests/test_billing_webhook_isolation.py`).

- [x] `P0-02` Eliminate unobserved fire-and-forget billing side effects. (`M`)
  - Why: webhook schedules email side effects with `asyncio.create_task(...)` and does not observe completion/failure.
  - Evidence: `app/api/billing.py` (email scheduling branches in webhook handler).
  - Done when: side effects are moved to a tracked background mechanism (or explicitly awaited in a safe pattern), and failures are captured with correlation metadata (request/event id).
  - Completed: 2026-03-24 (`app/api/billing.py`, `tests/test_billing_webhook_tasks.py`).

## P1 - Security, Observability, and Maintainability

- [x] `P1-01` Add CSRF validation to guest upload mutation routes. (`M`)
  - Why: guest upload endpoints mutate server state via cookie-authenticated requests but do not validate CSRF token.
  - Evidence: `app/api/uploads.py` (`POST /guest/upload/{event_code}`, `/delete`, `/restore`); `templates/guest_upload.html` has no CSRF hidden input.
  - Done when: guest upload form includes CSRF token, server validates token on all guest POST mutation routes, and tests cover reject/accept paths.
  - Completed: 2026-03-24 (`app/api/uploads.py`, `templates/guest_upload.html`, `static/js/pages/guest_upload.js`, `tests/test_guest_upload_triggers_order.py`, `tests/test_upload_limits.py`, `tests/test_guest_upload_mutation_csrf.py`).

- [x] `P1-02` Harden guest session cookie flags used for authorization. (`S`)
  - Why: guest cookie is used as an auth key for delete/restore but is set without `httponly` and without explicit `secure` behavior.
  - Evidence: `app/api/uploads.py` (`resp.set_cookie(cookie_name, str(guest_id), ..., samesite="lax")`).
  - Done when: cookie uses `httponly=True`, secure policy is environment-driven, and behavior is documented/tested for local and production.
  - Completed: 2026-03-24 (`app/api/uploads.py`).

- [x] `P1-03` Reduce broad exception swallowing in billing utilities. (`M`)
  - Why: many `except Exception` blocks in core billing helper paths hide real failures and complicate payment support.
  - Evidence: `app/services/billing_utils.py` (multiple broad catch blocks across plan resolution and entitlement logic).
  - Done when: catches are narrowed to expected exception types and each recovery path logs actionable context.
  - Completed: 2026-03-24 (`app/services/billing_utils.py`, `tests/test_billing_utils_exceptions.py`).

- [x] `P1-04` Reduce broad exception swallowing in Stripe webhook flow. (`M`)
  - Why: webhook has nested broad catches, including non-logging `pass` branches in critical reconciliation paths.
  - Evidence: `app/api/billing.py` (multiple nested `except Exception` blocks around addon/purchase updates and logging).
  - Done when: expected failures are handled explicitly, unexpected failures are logged with event/session identifiers, and behavior remains idempotent.
  - Completed: 2026-03-24 (`app/api/billing.py`, `tests/test_billing_webhook_negative_paths.py`).

- [x] `P1-05` Optimize and validate admin audit export filtering inputs. (`S`)
  - Why: current filtering serializes each log record (`json.dumps(obj)`) for substring matching and does not constrain filter input size.
  - Evidence: `app/api/admin.py` (`/admin/audit-logs/export` filter loop).
  - Done when: matching avoids per-line full serialization for `type_hint`, query params are length-constrained, and tests validate filter correctness and bad-input handling.
  - Completed: 2026-03-24 (`app/api/admin.py`, `tests/test_admin_audit_export.py`).

- [x] `P1-06` Add failure-side audit logs for guest upload mutations. (`S`)
  - Why: successful guest delete/restore actions are audited, but authorization/not-found failure branches are not consistently observable.
  - Evidence: `app/api/uploads.py` guest delete/restore routes.
  - Done when: deny/not-found/error outcomes emit audit events with event code, guest cookie presence, and request id.
  - Completed: 2026-03-24 (`app/api/uploads.py`, `tests/test_guest_upload_failure_audit.py`).

## P2 - Coverage and Regression Guardrails

- [x] `P2-01` Add compression middleware behavior tests. (`S`)
  - Why: gzip middleware exists but there is no explicit test that verifies compressed responses under normal browser accept-encoding behavior.
  - Evidence: `app/core/middleware_compression.py`; no matching assertions in `tests/` for compression headers.
  - Done when: tests assert `Content-Encoding` behavior for compressible responses and ensure small responses are not over-compressed.
  - Completed: 2026-03-24 (`tests/test_compression_middleware.py`, 4 tests covering large/small responses, Accept-Encoding header, and JSON responses).

- [x] `P2-02` Add negative-path Stripe webhook tests. (`M`)
  - Why: webhook happy-path/idempotency is covered, but malformed/signature-failure coverage is thin.
  - Evidence: `tests/test_extras_webhook.py`, `tests/test_webhook_idempotency.py` (mostly success paths).
  - Done when: tests cover invalid signature, malformed payload, and missing expected object fields without regressions.
  - Completed: 2026-03-24 (`tests/test_billing_webhook_negative_paths.py`).

- [x] `P2-03` Add explicit legacy `/addons` redirect coverage. (`S`)
  - Why: `/plans` redirect has test coverage, but equivalent backward-compat route coverage for `/addons` is missing.
  - Evidence: tests include `/plans` redirect check in `tests/test_billing_checkout.py`; no `/addons` redirect assertions found.
  - Done when: tests verify `/addons` redirect target/status and a deprecation note is captured in docs/changelog.
  - Completed: 2026-03-24 (`tests/test_legacy_addons_redirect.py`, 2 tests covering redirect status and query string preservation).

## Suggested Execution Order

1. Security and payment reliability: `P0-01`, `P0-02`, `P1-01`, `P1-02`
2. Billing/ops observability: `P1-03`, `P1-04`, `P1-05`, `P1-06`
3. Regression guardrails: `P2-01`, `P2-02`, `P2-03`

## Tracking Notes

- 2026-03-24: New full-site review completed and backlog reset to currently open items.
- 2026-03-24: Previous 2026-03-23 backlog retained as historical completion ledger in `WEBSITE_REVIEW_2026-03-23.md`.
- 2026-03-24: Completed `P0-01` by replacing raw webhook isolation SQL with dialect-aware `sqlalchemy.text(...)` execution and focused tests.
- 2026-03-24: Completed `P0-02` by replacing fire-and-forget webhook task scheduling with tracked callbacks that log completion failures.
- 2026-03-24: Completed `P1-01` by adding guest CSRF issuance/validation to upload, delete, and restore flows with positive/negative tests.
- 2026-03-24: Completed `P1-02` by hardening guest session cookie attributes (`HttpOnly`, env-driven `Secure`, explicit path).
- 2026-03-24: Completed `P1-03` by narrowing billing utility exception handling and adding focused logging/coverage for reconciliation and provisioning failures.
- 2026-03-24: Completed `P1-04` by narrowing webhook exception catches, removing silent fallback swallowing, and adding malformed/signature failure tests.
- 2026-03-24: Completed `P1-05` by constraining audit export filter input lengths and replacing per-line full-object serialization with targeted type-hint field matching.
- 2026-03-24: Completed `P1-06` by adding failure-side audit.warning() calls to guest upload delete/restore/list denials with structured context (reason, event_code, event_id, file_id, guest_cookie_present, request_id) and 5 targeted tests covering no-cookie, invalid-csrf, and file-not-found paths.
- 2026-03-24: Completed `P2-01` by adding 4 compression middleware tests that verify gzip encoding for responses >= 500 bytes, skipping compression for small responses, respecting Accept-Encoding headers, and handling JSON responses.
- 2026-03-24: Completed `P2-02` by adding webhook negative-path tests for malformed payloads, invalid signatures, and missing object fields.
- 2026-03-24: Completed `P2-03` by adding 2 tests for the legacy `/addons` redirect route that verify 307 status code and query string preservation to `/extras` target.
