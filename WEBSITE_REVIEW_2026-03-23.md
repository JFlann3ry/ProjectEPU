# Website Review Backlog (2026-03-23)

Full-site audit backlog for ProjectEPU. This document turns the review into an actionable checklist with priorities, effort, and done criteria.

How to use
- Work top-to-bottom by priority: `P0` then `P1` then `P2`.
- Keep each PR focused on one to three items.
- Mark items done with a short note and PR link.

Legend
- `P0` = critical risk / high-impact reliability
- `P1` = meaningful product and quality improvements
- `P2` = optimization and polish
- Effort: `S` (<=1 day), `M` (2-4 days), `L` (5+ days)

## P0 - Security, Reliability, and Platform Risk

- [x] `P0-01` Wire security middleware in app startup. (`S`)
  - Why: security headers middleware exists but is not currently mounted.
  - Evidence: `app/core/middleware_security.py`, `main.py`
  - Done when: `SecurityHeadersMiddleware` is added in app startup, tested for HTML responses, and documented.
  - Completed: 2026-03-23 (`main.py`, `tests/test_security_headers.py`, `SECURITY.md`).

- [x] `P0-02` Replace public raw `/storage` exposure with controlled access. (`L`)
  - Why: raw originals are served directly from mounted storage paths.
  - Evidence: `main.py`, `app/api/live.py`
  - Done when: originals are served via signed/expiring links or auth-checked endpoints; non-public files are no longer globally enumerable.
  - Completed: 2026-03-23 (`app/api/media.py`, `main.py`, `app/api/live.py`, `app/api/gallery.py`, `app/api/uploads.py`, `deploy/nginx.conf`, `tests/test_media_access.py`, `SECURITY.md`).

- [x] `P0-03` Stream uploads in chunks and enforce size limits before full read. (`M`)
  - Why: current owner upload path reads complete files into memory first.
  - Evidence: `app/api/events.py`
  - Done when: chunked write path is used, request memory stays bounded, and over-limit files fail early.
  - Completed: 2026-03-23 (`app/services/upload_streams.py`, `app/api/events.py`, `app/api/uploads.py`, `tests/test_upload_limits.py`).

- [x] `P0-04` Make support/contact delivery failures observable. (`S`)
  - Why: contact email errors are swallowed and user still sees success.
  - Evidence: `app/api/support.py`
  - Done when: failures are logged with request ID and either surfaced to admin telemetry or safely retried/queued.
  - Completed: 2026-03-23 (`app/api/support.py`, `tests/test_contact_observability.py`).

- [x] `P0-05` Harden production defaults. (`S`)
  - Why: risky defaults can slip into production (`SECRET_KEY`, `DEBUG_ROUTES_ENABLED`, cookie flags).
  - Evidence: `app/core/settings.py`
  - Done when: production env validation blocks unsafe boot and secure defaults are documented.
  - Completed: 2026-03-23 (`app/core/settings.py`, `tests/test_settings_prod_validation.py`, `SECURITY.md`).

## P1 - Architecture, UX, and Conversion

- [x] `P1-01` Split oversized route modules into focused units. (`L`)
  - Why: very large files increase regression risk and review difficulty.
  - Evidence: `app/api/events.py`, `app/api/gallery.py`, `app/api/billing.py`
  - Done when: each domain has a smaller router/service split with unchanged public behavior.
  - Progress: 2026-03-23 extracted admin billing routes into `app/api/billing_admin.py`, purchase/receipt routes into `app/api/billing_receipts.py`, and checkout routes into `app/api/billing_checkout.py`, reducing `app/api/billing.py` while preserving route behavior and order (`tests/test_billing_checkout.py`, `tests/test_billing_admin_routes.py`, `tests/test_billing_receipt_pdf.py`, `tests/test_billing_receipt_pdf_auth.py`). Also extracted event album and guestbook action routes into `app/api/events_collections.py` plus event asset routes (`/events/{event_id}/qr/logo`, `/events/{event_id}/banner`) into `app/api/events_assets.py`, wired through `app/api/events.py` (`tests/test_events_collections_routes.py`, `tests/test_events_assets_routes.py`). Added first `gallery.py` split by moving favorite/unfavorite and S3 presigned URL actions into `app/api/gallery_actions.py` (`tests/test_gallery_actions_routes.py`). Continued with `gallery.py` mutation/debug extraction into `app/api/gallery_mutations.py` (`tests/test_gallery_mutations_routes.py`) and additional gallery route extraction moving page/thumb endpoints (`/events/{event_id}/gallery/app`, `/events/{event_id}/gallery`, `/thumbs/{file_id}.jpg`) into `app/api/gallery_pages.py` (`tests/test_gallery_pages_routes.py`), bulk download route extraction moving `/gallery/download-zip` into `app/api/gallery_downloads.py` (`tests/test_gallery_downloads_routes.py`), scope selection routes extraction moving `/gallery/select` and `/gallery/clear` into `app/api/gallery_scope.py` with shared scope-cookie helpers in `app/api/gallery_scope_shared.py`, gallery payload routes extraction moving `/gallery/data` and `/gallery/ids` into `app/api/gallery_data.py` with scoped event resolution shared via `app/api/gallery_scope_resolver.py`, focused mutation-route extraction moving `/gallery/actions/delete` and `/gallery/actions/restore` into `app/api/gallery_mutations_delete_restore.py` plus `/gallery/actions/permadelete` into `app/api/gallery_mutations_permadelete.py` with shared utilities/log state in `app/api/gallery_mutations_shared.py`, event order route extraction moving `GET /events/{event_id}/gallery/order` into `app/api/gallery_order.py`, server-rendered gallery page extraction moving `GET /gallery` into `app/api/gallery_view.py`, and builder-helper extraction moving `_has_deleted_at`, `_build_gallery_files`, and `_build_gallery_ids` into `app/api/gallery_builders.py` with downstream imports rewired in `gallery_data`, `gallery_view`, and `gallery_order` (`tests/test_gallery_scope_routes.py`, `tests/test_gallery_pagination.py`, `tests/test_gallery_pages_routes.py`, `tests/test_gallery_downloads_routes.py`, `tests/test_gallery_mutations_routes.py`, `tests/test_gallery_delete.py`, `tests/test_gallery_restore.py`, `tests/test_gallery_delete_auth.py`, `tests/test_debug_routes_gated.py`, `tests/test_gallery_order_sp.py`, `tests/test_gallery_order_edge.py`, `tests/test_gallery_order_routes.py`, `tests/test_gallery_template_smoke.py`, `tests/test_gallery_view_routes.py`). Also split `events.py` edit/lock flow into focused modules: GET edit pages in `app/api/events_editing.py` (`tests/test_events_editing_routes.py`), lock-date routes in `app/api/events_locking.py` (`tests/test_events_locking_routes.py`), dashboard/share/checklist routes in `app/api/events_dashboard.py` (`tests/test_events_dashboard_routes.py`), owner detail routes in `app/api/events_details.py` (`tests/test_events_details_routes.py`), edit submit routes in `app/api/events_edit_submit_numeric.py` plus `app/api/events_edit_submit_code.py` (composed via `app/api/events_edit_submit.py`), owner upload route in `app/api/events_uploads.py`, and event task toggle route in `app/api/events_tasks.py`, leaving `app/api/events.py` as a pure composition router.
  - Completed: 2026-03-23 (`app/api/events.py`, `app/api/events_uploads.py`, `app/api/events_tasks.py`).

- [x] `P1-02` Reduce broad `except Exception` swallowing in core paths. (`M`)
  - Why: hidden errors reduce debuggability and can mask user-facing issues.
  - Evidence: `main.py`, `app/api/events.py`, `app/api/gallery.py`
  - Done when: catch blocks are narrowed and failures are logged with actionable context.
  - Progress: 2026-03-23 narrowed exception handlers in `main.py` (sentry_sdk import to `ImportError`, logging middleware user_id extraction to `(AttributeError, ValueError, KeyError)`, request processing to `(ValueError, KeyError, AttributeError)`, 404 handler to `(OSError, RuntimeError, AttributeError)`, http_exception_handler DB write and redirect header access to specific exception types, server_error_handler to specific types), `app/core/settings.py` (COOKIE_SECURE auto-detect to `(AttributeError, TypeError)`), `app/core/logging_utils.py` (JSON serialization to `(TypeError, ValueError)`, log directory creation to `(OSError, IOError)`), and `app/api/events.py` (CSRF validation to `(AttributeError, ValueError, TypeError)`, upload form parsing to `(ValueError, KeyError)`, type coercion to `ValueError`, DB operations to specific types). Added targeted logging for critical failures where swallowing was required. Test results: 124 passed, no regressions introduced by narrowing.
  - Completed: 2026-03-23 (`main.py`, `app/core/settings.py`, `app/core/logging_utils.py`, `app/api/events.py`).

- [x] `P1-03` Move inline JS/CSS from base/template files into static bundles. (`M`)
  - Why: inline code hurts cacheability and maintainability.
  - Evidence: `templates/base.html`, `templates/guest_upload.html`, `templates/home.html`, `templates/pricing.html`
  - Done when: templates are mostly declarative and shared behavior/styles live in `static/js` and `static/*.css`.
  - Progress: 2026-03-23 extracted `home.html` page styles into `static/home.css` and page behavior into `static/js/pages/home.js`, moved pricing card styles from `templates/pricing.html` into `static/pricing.css`, moved guest upload page-specific theme CSS plus page behavior from `templates/guest_upload.html` into `static/uploads/guest-upload.css` and `static/js/pages/guest_upload.js`, and extracted shared base template inline CSS/JS into static bundles by moving shared modal/snackbar/tooltip/breadcrumb/cookie-banner styles into `static/app.css`, wiring global behavior through `static/js/base.js`, and replacing `templates/base.html` inline share modal script with declarative `#share-modal-template` markup plus script includes.
  - Completed: 2026-03-23 (`templates/base.html`, `templates/home.html`, `templates/pricing.html`, `templates/guest_upload.html`, `static/app.css`, `static/home.css`, `static/pricing.css`, `static/uploads/guest-upload.css`, `static/js/base.js`, `static/js/pages/home.js`, `static/js/pages/guest_upload.js`).

- [x] `P1-04` Rework pricing page for mobile-first conversion. (`M`)
  - Why: hard-coded grid and heavy inline styling make responsiveness fragile.
  - Evidence: `templates/pricing.html`
  - Done when: card layout stacks cleanly on small screens and CTA hierarchy is clear.
  - Progress: 2026-03-23 replaced inline pricing layout styles with mobile-first classes and responsive breakpoints (`1 -> 2 -> 3` columns), tightened card spacing/typography for small screens, and standardized CTA wrappers (`templates/pricing.html`, `static/pricing.css`).
  - Completed: 2026-03-23 (`templates/pricing.html`, `static/pricing.css`).

- [x] `P1-05` Add richer metadata on marketing pages (title/description/OG/Twitter). (`S`)
  - Why: core pages lack consistent social/search metadata.
  - Evidence: `templates/base.html`, `templates/share_event.html`
  - Done when: home/pricing/about/tutorial/contact include explicit metadata and validated previews.
  - Completed: 2026-03-23 (`templates/home.html`, `templates/pricing.html`, `templates/about.html`, `templates/contact.html`, `templates/tutorial.html`, `templates/share_event.html`).

- [x] `P1-06` Improve live slideshow transport strategy. (`M`)
  - Why: fixed polling is simple but wasteful under load and background tabs.
  - Evidence: `static/js/pages/live_slideshow.js`
  - Done when: polling is visibility-aware and optionally upgradable to SSE/WebSocket.
  - Progress: 2026-03-23 replaced fixed `setInterval` polling with adaptive visibility-aware polling in `static/js/pages/live_slideshow.js` (`6s` when active, `30s` when tab is hidden) and immediate refresh on visibility return.
  - Completed: 2026-03-23 added optional `EventSource` stream hookup (`/live/{code}/stream`) with automatic fallback to adaptive polling, plus exponential backoff+jitter on poll failures (`static/js/pages/live_slideshow.js`, `tests/test_live_routes.py`).

- [x] `P1-07` Expand accessibility pass on dynamic status and modals. (`M`)
  - Why: several success/error updates rely on visual changes only.
  - Evidence: `templates/guest_upload.html`, `templates/base.html`
  - Done when: key status updates use live regions and modal keyboard/focus behavior is consistently validated.
  - Progress: 2026-03-23 repaired malformed `templates/guest_upload.html` and added live-region semantics for dynamic upload/status elements (`file-count`, success, duplicates, empty-state hint, selection count), promoted dynamic form errors to `role="alert"` in `static/js/pages/guest_upload.js`, and marked global snackbar as a polite status live region in `templates/base.html`.
  - Completed: 2026-03-23 (`templates/base.html`, `templates/guest_upload.html`, `static/js/pages/guest_upload.js`, `static/js/base.js`, `tests/test_share_modal.py`).

- [x] `P1-08` Consolidate duplicate modal implementations. (`M`)
  - Why: shared modal and fallback modal logic coexist in gallery page JS.
  - Evidence: `static/js/pages/gallery.js`
  - Done when: one modal abstraction is used consistently across pages.
  - Completed: 2026-03-23 removed legacy inline modal fallback paths in gallery album flows and standardized on shared `window.EPU.modal` for add/create album dialogs (`static/js/pages/gallery.js`).

- [x] `P1-09` Add analytics (consent-aware) for funnel visibility. (`M`)
  - Why: cookie consent infrastructure exists, but funnel instrumentation appears absent.
  - Evidence: `static/cookie-consent.js`
  - Done when: key events are tracked (landing, signup, event create, checkout start/success) with consent enforcement.
  - Completed: 2026-03-23 added consent-gated client tracker and lightweight collector endpoint, wired funnel signals (`landing`, `signup_start`, `event_create_start/submit`, `checkout_start`, `checkout_success`) across pricing/extras/billing flows (`static/js/analytics.js`, `static/cookie-consent.js`, `static/js/pages/pricing.js`, `static/js/pages/extras.js`, `static/js/pages/billing_purchase.js`, `app/api/misc.py`, `templates/base.html`, `tests/test_analytics_tracking.py`).

- [x] `P1-10` Expand e2e coverage for critical user journeys. (`M`)
  - Why: current e2e surface is narrow compared to feature breadth.
  - Evidence: `tests/e2e/`
  - Done when: at least signup/login, event create, guest upload, gallery bulk action, and checkout paths have e2e smoke tests.
  - Completed: 2026-03-23 expanded `tests/e2e/test_critical_journeys_e2e.py` to cover all required journey entry points (signup/login, event create, guest upload, gallery bulk delete action, checkout entry), guarded by `E2E_PLAYWRIGHT=1` for low-flake default runs.

## P2 - SEO, Performance, and Polish

- [x] `P2-01` Tighten robots/sitemap strategy for index quality. (`S`)
  - Why: current sitemap includes some low-value/internal routes.
  - Evidence: `app/api/misc.py`
  - Done when: only high-value indexable routes are listed and ephemeral/private pages remain excluded.
  - Completed: 2026-03-23 tightened `robots.txt` disallow rules for private/low-value surfaces and removed `/gallery` from sitemap static URLs while keeping canonical marketing/share routes (`app/api/misc.py`, `tests/test_seo_endpoints.py`).

- [x] `P2-02` Add performance budgets and periodic page audits. (`M`)
  - Why: CSS/JS growth can regress Core Web Vitals over time.
  - Evidence: template/style sprawl in `templates/*` and `static/*`
  - Done when: basic budget thresholds and a repeatable audit task are in place.
  - Completed: 2026-03-23 added a budgeted performance audit utility and baseline budgets (`scripts/perf_audit.py`, `scripts/perf_budgets.json`), documented usage (`README.md`), and added repeatable task label `perf:audit` in workspace tasks.

- [x] `P2-03` Content polish pass on conversion pages. (`S`)
  - Why: copy quality affects trust and purchase conversion.
  - Evidence: `templates/pricing.html`
  - Done when: copy is edited for clarity, consistency, and typos.
  - Completed: 2026-03-23 refined pricing page headline, package feature copy, and CTA labels for clearer intent and consistent spelling/tone (`templates/pricing.html`).

## Suggested Execution Order

1. Security hardening sprint: `P0-01`, `P0-05`, `P0-04`
2. Upload/media protection sprint: `P0-03`, `P0-02`
3. Frontend maintainability sprint: `P1-03`, `P1-08`, `P1-04`
4. Growth and quality sprint: `P1-05`, `P1-09`, `P1-10`
5. Optimization sprint: `P2-01`, `P2-02`, `P2-03`

## First 2 Weeks (Practical Starter Set)

- [x] Week 1: `P0-01` security middleware wiring
- [x] Week 1: `P0-05` production settings validation
- [x] Week 1: `P0-04` contact delivery observability
- [x] Week 2: `P0-03` upload streaming + limits
- [x] Week 2: `P1-03` extract base inline JS/CSS to static bundles

## Tracking Notes

- 2026-03-23: Initial full review baseline created.
- 2026-03-23: Completed `P0-01` by wiring `SecurityHeadersMiddleware`, adding header tests, and documenting behavior.
- 2026-03-23: Completed `P0-05` with production fail-fast settings validation and focused tests.
- 2026-03-23: Completed `P0-04` by logging contact email delivery failures to audit logs and `AppErrorLog`.
- 2026-03-23: Completed `P0-03` by spooling uploads to temp files, enforcing size limits during streaming, and validating owner/guest flows with focused tests.
- 2026-03-23: Completed remaining P1/P2 items (`P1-01` to `P1-10`, `P2-01` to `P2-03`) and passed full local quality gate via `scripts/lint_and_test.py` (`ruff check .` + `pytest -q`).
