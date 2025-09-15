### Security headers & CSRF
## Goal
- Strengthen default security posture with standard headers and consistent CSRF on all POST forms.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Add a small middleware to set headers: `Strict-Transport-Security` (prod-only), `X-Frame-Options=DENY`, `X-Content-Type-Options=nosniff`, `Referrer-Policy=strict-origin-when-cross-origin`, and a conservative `Content-Security-Policy` (block inline, allow self + required CDNs only).
- [ ] Enable GZip/deflate compression middleware.
- [ ] Audit POST forms and add CSRF everywhere (events create/edit, profile, admin actions, guest upload); tests for CSRF rejection and success.

## Acceptance
- [ ] All responses include headers above (visible in browser/devtools).
- [ ] All POST forms include a CSRF token and reject invalid/missing tokens (except TestClient bypass in tests).

==========================================

### Protect media: signed/auth downloads
## Goal
- Avoid exposing private media via public `/storage`; gate downloads using signed URLs and auth.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Remove static mount for `/storage` in production; keep in dev.
- [ ] Add `/download/{signed}` endpoint to serve files after validating HMAC + expiry + authorization (owner or allowed).
- [ ] Generate signed URLs with short TTL for gallery/bulk download; set `Cache-Control` appropriately (no-store for private).
- [ ] Optional: presigned URLs if/when moved to S3/Blob storage.

## Acceptance
- [ ] Direct `/storage/...` is not publicly routable in prod.
- [ ] Valid signed URLs download; expired/invalid return 403.

==========================================

### Email program: templates, queue, preferences, logging
## Goal
- Implement EMAIL_PROGRAM.md with templates, throttling, preferences, and delivery logging.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Create `templates/emails/{key}.html` for top-priority transactional emails (verify, reset, invoice, payment_failed, event reminders).
- [ ] Add `EmailLog` model (Key, To, Status, Error, RequestID, CreatedAt); Alembic migration.
- [ ] Wrap send function: records EmailLog, respects UserEmailPreference (marketing/product/reminders), applies throttling rules.
- [ ] Add background queue (APScheduler/RQ/Celery) for async sends; retry on transient errors.
- [ ] Add List-Unsubscribe to marketing/education messages.
- [ ] Update README with SPF/DKIM/DMARC guidance; allow swapping SMTP for provider (SendGrid/SES/Mailgun).

## Acceptance
- [ ] Emails render with variables, send asynchronously, and are recorded in EmailLog.
- [ ] Marketing/education emails suppressed if user is opted-out.

==========================================

### Stripe & billing robustness
## Goal
- Make billing/webhooks resilient and auditable.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Add `STRIPE_WEBHOOK_SECRET` to `app/core/settings.py` (+ .env.example) and verify webhook signatures.
- [ ] Use idempotency keys on client-side Stripe operations; ignore duplicate webhook events.
- [ ] Implement dunning emails: `billing.payment_failed`, `billing.card_expiring`, `billing.invoice_issued` using new email templates.
- [ ] Tests: bad signature, duplicate events, success path.

## Acceptance
- [ ] Webhooks fail closed without a valid signature.
- [ ] Duplicate events do not create duplicate records.

==========================================

### Add-ons: complete the loop
## Goal
- Finish add-on catalog management, purchase flow, and limit enforcement.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Admin UI to CRUD `AddonCatalog` entries.
- [ ] Seed script for common add-ons; document usage.
- [ ] Purchase flow on Extras/Billing pages; create `EventAddonPurchase` rows; receipt email.
- [ ] Enforce effective limits = plan + sum(add-ons) across upload/storage/features.
- [ ] Show add-on usage on Billing summary.

## Acceptance
- [ ] Add-ons can be listed, purchased, and enforced; purchases appear in Billing summary.

==========================================

### Background jobs & schedulers
## Goal
- Move slow/periodic work off request thread and schedule product emails.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Add a scheduler for reminders: T-7, T-1, Day-of, T+1 wrap-up (respect prefs; dedupe).
- [ ] Guest upload digest (daily/weekly) when new uploads exist.
- [ ] Run data export completion emails from background job.
- [ ] Centralize job logging and failure alerts.

## Acceptance
- [ ] Reminders/digests fire at expected times with logs; no blocking of web requests.

==========================================

### CI/CD improvements
## Goal
- Broaden coverage and speed up CI on feature branches; add type safety.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Trigger CI on `dev` and PRs to `dev`; cache pip to speed up runs.
- [ ] Add mypy with an initial baseline; type key services/models and fail on new issues.
- [ ] Parallelize lint/test jobs; upload logs/artifacts on failure.
- [ ] Add pre-commit checks in CI (ruff/black/mypy).

## Acceptance
- [ ] CI runs on dev/PRs, completes faster, and fails on new typing errors.

==========================================

### Observability & ops
## Goal
- Improve tracing/metrics and make container logging standard.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Increase Sentry `traces_sample_rate` for key routes (uploads, exports) in prod; add custom spans in heavy code paths.
- [ ] Add basic Prometheus metrics (request count/latency, queue depth) or equivalent; expose `/metrics` if chosen.
- [ ] In Docker, prefer logging to stdout; move file rotation to host if needed.

## Acceptance
- [ ] Key routes appear in tracing; metrics available for dashboards; container logs are clean.

==========================================

### Data lifecycle & privacy
## Goal
- Define and enforce retention for deleted content, exports, and sessions; finalize account deletion flow.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Scheduled purge of soft-deleted media after N days; configurable.
- [ ] Purge expired export ZIPs (older than 7 days) and stale sessions.
- [ ] Account deletion: grace window, final purge job, send `account.deleted` email.
- [ ] Document retention policies in README/Privacy.

## Acceptance
- [ ] Purge jobs run and log; storage and DB no longer accumulate expired data.

==========================================

### Tests to add
## Goal
- Increase coverage for critical flows and security controls.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Webhooks: signature verification, idempotency, dunning path.
- [ ] Email: preference enforcement and throttling; templating variables validated.
- [ ] Add-ons: list/purchase/enforce; billing summary reflects purchases.
- [ ] CSRF: create/edit forms and admin actions; signed download URLs.
- [ ] Upload edges: size/type limits; MIME sniff mismatch handling.

## Acceptance
- [ ] New tests pass locally and in CI; regressions are caught by CI.

==========================================

### Deployment polish
## Goal
- Harden Docker/systemd+Nginx and production configs.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Docker: add non-root user, healthcheck, slimmer image (multi-stage), env-only config, and proper signals/uvicorn workers.
- [ ] Nginx: security headers, gzip, caching rules for static, proxy for `/download` only.
- [ ] Production toggle to disable `/storage` static mount.
- [ ] Add `STRIPE_WEBHOOK_SECRET` to `.env.example` and docs; document secret management.

## Acceptance
- [ ] Container passes healthcheck; Nginx serves with security headers; `/storage` is gated in prod.

==========================================

### Template JS cleanup & modularization
## Goal
- Reduce inline JavaScript in templates, improve reuse/maintainability, and enable a strict CSP without `unsafe-inline`.

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Audit templates for inline scripts and inline event handlers (e.g., `onclick`). List pages with > ~30 lines or reused logic.
- [ ] Establish structure under `static/js/`:
	- `static/js/pages/` for page-specific modules (e.g., `events_dashboard.js`, `gallery.js`).
	- `static/js/components/` for reusable widgets (e.g., `copy_to_clipboard.js`, `snackbar.js`).
	- `static/js/utils/` for helpers (e.g., `dom.js`, `api.js`).
- [ ] Convert inline scripts to ES modules loaded with `type="module"` and `defer`; import shared components where needed.
- [ ] Replace inline event attributes (e.g., `onclick`) with delegated listeners in modules; use `data-*` attributes for hooks.
- [ ] Add a Jinja block or helper in `base.html` to load per-page modules cleanly (e.g., `{% block extra_js %}{% endblock %}`).
- [ ] Introduce a conservative CSP (paired with the security headers task) that disallows inline scripts; during transition, use nonces only where unavoidable.
- [ ] Optional: add a tiny bundler step for production (esbuild) for minification and HTTP/2-friendly chunking.
- [ ] Optional: add ESLint (flat config) for `static/js/**` and run it in CI.
- [ ] Document conventions in `README.md` (where to place code, naming, and how to add new page scripts).

## Acceptance
- [ ] Templates have no significant inline JS; only minimal bootstraps remain if any.
- [ ] Page behavior is implemented via `static/js/pages/*.js` and shared logic in `static/js/components/*`.
- [ ] Site works under a CSP without `unsafe-inline` for scripts.
- [ ] Reused behaviors exist in one place and are imported where needed.

#### Pages to migrate (JS)
- [ ] templates/edit_event.html
- [ ] templates/event_details.html (Stripe + add-on buy)
- [ ] templates/pricing.html (Stripe checkout)
- [ ] templates/billing_purchase.html (Stripe retry/email)
- [ ] templates/extras.html (Stripe buy)
- [ ] templates/extras.html (Stripe buy)
- [ ] templates/guest_upload.html (XHR upload logic)
- [ ] templates/events_dashboard.html
- [ ] templates/create_event.html
- [ ] templates/profile.html (email prefs modal)
- [ ] templates/edit_profile.html (export/password flows)
- [ ] templates/contact.html
- [ ] templates/account_delete.html
- [ ] templates/account_delete_confirmed.html
- [ ] templates/admin_themes.html (editor interactions)
- [ ] templates/admin_components.html
- [ ] templates/faq.html (accordion)
- [ ] templates/components/lightbox.html
- [ ] templates/share_event.html (copy link)
- [ ] templates/examples.html (preview modal triggers)
- [ ] templates/base.html (global modal/snackbar/nav/tooltip) — later split into components and loaded sitewide
- [x] templates/gallery.html — migrated to `static/js/pages/gallery.js` (remaining: replace inline lightbox onclick handlers and consider merging `static/gallery.js`)

==========================================

### Template dedupe: hero/notice macros
## Goal
- Replace duplicated page-hero and notice blocks with macros for consistency.

## Build
- [x] Refactor templates/gallery.html
- [x] Refactor templates/profile.html
- [x] Refactor templates/create_event.html
- [x] Refactor templates/events_dashboard.html
- [x] Refactor templates/terms.html
- [x] Refactor templates/edit_profile.html
- [x] Refactor templates/billing_summary.html
- [x] Refactor templates/log_in.html
- [x] Refactor templates/sign_up.html
- [x] Refactor templates/pricing.html
- [x] Refactor templates/about.html
- [x] Refactor templates/faq.html
- [x] Refactor templates/tutorial.html
- [x] Refactor templates/contact.html
- [x] Refactor templates/privacy.html
- [ ] Sweep remaining templates for .page-hero and .notice and migrate

## Next
- [x] Extract breadcrumbs and button rows into macros; replace repetitive blocks
- [x] Add chip/badge helper for status labels (paid/pending/etc.)

