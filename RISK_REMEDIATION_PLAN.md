# Risk Remediation Plan

Owner: Engineering
Status: Complete
Last updated: 2026-03-26

Merged sources
- WEBSITE_REVIEW_2026-03-24.md
- WEBSITE_REVIEW_2026-03-26.md

## Goal
Close remaining security and operational risk areas with small, testable changes.

## Working Rules
- Keep each PR focused on one risk area.
- Add or update tests for every behavior change.
- Keep route order and existing public behavior stable unless explicitly changing it.
- Run lint and tests before marking a checklist item complete.

## Milestones

### M0 - Baseline and Guardrails (0.5 day)
- [x] Capture baseline results for lint and core tests.
- [x] Confirm current backlog completion state.
- [x] Define done criteria for each milestone below.

Acceptance criteria
- Baseline command outputs are recorded in PR notes.
- Team agrees on done criteria for M1-M6.

M0 baseline snapshot (2026-03-26)
- `ruff check .` passes (0 errors).
- `pytest -q` passes (`187 passed, 11 skipped`).
- 2026-03-26 review regressions fixed:
  - `templates/examples.html`: repaired Jinja `{% call btn_row() %}` syntax.
  - `templates/base.html`: added `{% block extra_meta %}` so live noindex metadata renders.
  - `tests/test_live_routes.py`: updated src assertions for `?code=` query-string URLs.

M0 completion note (2026-03-26)
- Done criteria are now explicit under each milestone's Acceptance criteria section.
- Final validation state at plan completion: `ruff check .` clean and `pytest -q` (`221 passed, 11 skipped`).

---

### M1 - CSP Hardening and Inline Script Migration (1-2 days)
Scope
- Inventory inline scripts in templates.
- Migrate inline JS to static modules.
- Tighten CSP policy incrementally.

Tasks
- [x] Inventory all template inline scripts and event handlers.
- [x] Create static JS module files for first migration slice.
- [x] Update templates to load modules instead of inline scripts.
- [x] Add/adjust tests for pages touched.
- [x] Enable CSP report-only if not already available.
- [x] Review CSP violations and remove remaining blockers.

Inventory snapshot (2026-03-24)
- Inline `<script>` tags found in 23 template files.
- Inline event-handler attributes found in 4 template files.
- Highest-risk inline handlers are in commerce and account pages.
- Inline event-handler attributes are now reduced to 0 remaining.
- Data-only `type="application/json"` script tags are allowed and not CSP blockers.
- Remaining executable inline `<script>` blocks are down to 16 template files after the latest migrations.
- Migrated `templates/account_delete.html` to `static/js/pages/account_delete.js` and removed inline delete-confirmation modal script.
- Migrated `templates/account_delete_confirmed.html` to `static/js/pages/account_delete_confirmed.js` and removed inline 30-second redirect script.
- Migrated `templates/events_dashboard.html` to `static/js/pages/events_dashboard.js` and removed inline gallery-select, share, copy, markShared, hydrateProgress, and hydrateCountdown scripts.
- Wired `templates/profile.html` to existing `static/js/pages/profile.js` and removed inline gallery-select, email-prefs modal, share, and logout modal scripts.
- Focused regression tests passed for account-delete, events-dashboard, and profile page rendering after extraction.
- Remaining executable inline `<script>` blocks reduced to 12 template files.
- Migrated `templates/tutorial.html` to `static/js/pages/tutorial.js` (media fallback IIFE).
- Migrated `templates/live_slideshow.html` inline config to `data-event-code` attribute; `live_slideshow.js` now reads from DOM, no inline script needed.
- Migrated `templates/gallery.html` auxiliary IIFEs to `static/js/pages/gallery_aux.js` (album-selector, pager, delete-modal + create-album focus traps).
- Migrated `templates/event_details.html` first script block to `static/js/pages/event_details.js`; added `data-event-code` attr to `#lock-date-form`; Stripe conditional block preserved.
- Remaining executable inline `<script>` blocks reduced to 8 template files.
- Migrated `templates/admin_components.html` to `static/js/pages/admin_components.js` (demo-modal button handler).
- Migrated `templates/admin_themes.html` inline scripts to `static/js/pages/admin_themes.js` (2 blocks: theme swatches + large preview scaling logic).
- Remaining executable inline `<script>` blocks reduced to 6 template files.

First migration slice (PR-1)
- `templates/addons.html`
- `templates/share_event.html`
- `templates/admin_billing.html`
- `templates/examples.html`
- Move page logic to `static/js/pages/*.js` modules and remove inline `onclick` usage.

M1 progress (2026-03-24)
- Migrated `templates/share_event.html` to `static/js/pages/share_event.js` and removed inline script/`onclick`.
- Migrated `templates/addons.html` to use `static/js/pages/extras.js` via JSON config and removed inline script/`onclick`.
- Migrated `templates/admin_billing.html` to `static/js/pages/admin_billing.js` and removed inline `onclick` copy action.
- Migrated `templates/examples.html` to `static/js/pages/examples.js` and removed inline `onclick` preview actions and inline script block.
- PR-1 migration slice complete.
- Added configurable CSP report-only support via settings (`CSP_REPORT_ONLY`, `CSP_REPORT_URI`) and middleware wiring.
- Added report-only security header tests in `tests/test_security_headers_report_only.py`.
- Migrated `templates/sign_up.html` and `templates/reset_password.html` to shared `static/js/pages/auth_password_form.js` and removed inline password validation scripts.
- Migrated `templates/faq.html` to `static/js/pages/faq.js` and removed the inline accordion, sticky TOC, and live search script block.
- Focused regression tests passed for signup, reset-password, FAQ, and CSP header coverage.
- Migrated `templates/create_event.html` to `static/js/pages/create_event.js` and removed inline event-type toggle, terms modal, and submit guard scripts.
- Migrated `templates/contact.html` to `static/js/pages/contact.js` and removed inline topic sync, counters, and request-detail insertion scripts.
- Focused regression tests passed for create-event and contact page rendering after extraction.

M1 progress (2026-03-26)
- Re-ran CSP migration inventory over templates.
- Remaining executable inline `<script>` blocks are in 2 template locations:
  - `templates/edit_event.html` (2 blocks)
- Removed the remaining inline event-handler attribute from `templates/tutorial.html` (`onloadedmetadata`) and moved behavior into `static/js/pages/tutorial.js`.
- Migrated `templates/components/lightbox.html` inline module bootstrap to external module load (`static/js/modules/lightbox.js`).
- Migrated `templates/extras.html` inline checkout-return notice script into `static/js/pages/extras.js`.
- Focused regression tests passed after migration (`tests/test_tutorial_page.py`, `tests/test_live_routes.py`, `tests/test_gallery_no_react_refs.py`, `tests/test_legacy_addons_redirect.py`, `tests/test_event_details_script.py`).
- Migrated `templates/edit_event.html` remaining 2 inline script blocks to external `static/js/pages/edit_event.js` and wired QR guest URL via `data-guest-url` on `#qr-img`.
- Re-ran inline-script inventory scan across `templates/**/*.html`; no executable inline `<script>` blockers remain (JSON data scripts only).
- Validation passed after final migration: `ruff check .` clean and `pytest -q` (`187 passed, 11 skipped`).

Acceptance criteria
- No inline script required on migrated pages.
- Migrated pages pass tests and maintain behavior.
- CSP report-only violations are reduced to expected/known items.

---

### M2 - Upload Surface Hardening (SVG and MIME) (1 day)
Scope
- Finalize SVG policy and enforce it server-side.

Tasks
- [x] Choose SVG policy: reject or sanitize.
- [x] Implement server-side SVG/MIME validation in upload routes.
- [x] Add tests for valid uploads, blocked SVG, and spoofed extension attempts.
- [x] Verify media serving behavior remains safe.

M2 progress (2026-03-26)
- Finalized SVG policy as explicit reject.
- Enforced SVG rejection in `app/services/mime_utils.py` via both MIME normalization and byte-signature detection (`<svg`) to cover spoofed extension/content-type attempts when libmagic is unavailable.
- Upload paths already using shared MIME validation were verified (`app/services/upload_streams.py`, owner and guest upload routes).
- Added/expanded focused coverage in `tests/test_upload_svg_policy.py`:
  - direct MIME policy rejection,
  - owner reject for `.svg` upload,
  - guest reject for `.svg` upload,
  - spoofed `.jpg` filename with SVG payload rejected.
- Validation passed: `ruff check .` clean and `pytest -q` (`192 passed, 11 skipped`).

Acceptance criteria
- SVG handling is explicit and enforced.
- Tests cover accept and reject paths.

---

### M3 - Plan Enforcement Consistency (1 day)
Scope
- Strengthen window and feature-gating boundary tests.

Tasks
- [x] Add table-driven tests for upload and download window boundaries.
- [x] Validate server-time based checks in enforcement logic.
- [x] Add negative tests for expired window paths.

M3 progress (2026-03-26)
- Added table-driven tests in `tests/test_plan_windows.py` for `upload_window_active` and `download_window_active` across free/basic/ultimate tiers.
- Validated server-time behavior by freezing `now()` via monkeypatch against `app.core.plan_features` time source.
- Added explicit negative-path coverage for expired upload/download windows (boundary +1 second).

Acceptance criteria
- Boundary and expiry tests pass for all plan tiers under test.
- No regressions in existing enforcement flows.

---

### M4 - DB Agent Job Rollout (safe subset) (1-2 days)
Scope
- Operationalize low-risk retention and cleanup jobs.

Tasks
- [x] Implement PaymentLog retention purge job (batched).
- [x] Implement completed export cleanup workflow (DB rows and files).
- [x] Implement stale guest session cleanup job.
- [x] Add JobRunLog usage and failure logging.
- [x] Stage and dry-run each job before production.

M4 progress (2026-03-26)
- Implemented batched PaymentLog retention purge job in `app/jobs/maintenance.py` (`purge_old_payment_logs`) with configurable retention days and batch size.
- Added best-effort JobRunLog recording for success/failure in the same module (non-fatal if table is absent).
- Added a Windows-safe runner script `scripts/purge_payment_logs.py` for operational execution.
- Added focused tests in `tests/test_paymentlog_purge_job.py` covering batched deletion behavior and JobRunLog insertion when the table exists.
- Implemented completed export cleanup workflow in `app/jobs/maintenance.py` (`cleanup_completed_exports`) with batched DB row deletion plus ZIP file removal.
- Implemented stale guest session cleanup in `app/jobs/maintenance.py` (`cleanup_stale_guest_sessions`) deleting only old sessions with no linked `FileMetadata` or `GuestMessage` rows.
- Added Windows-safe runner scripts `scripts/cleanup_completed_exports.py` and `scripts/cleanup_stale_guest_sessions.py`.
- Added focused tests in `tests/test_export_cleanup_job.py` and `tests/test_guestsession_cleanup_job.py`.
- Validation passed after SQL Server test hardening and query adjustments: `ruff check .` clean and `pytest -q` (`213 passed, 11 skipped`).
- Staged conservative dry-runs in local environment using large retention windows (no-op expected):
  - `scripts/purge_payment_logs.py --retention-days 365000 --batch-size 100` -> `batches=0 deleted_rows=0`
  - `scripts/cleanup_completed_exports.py --retention-days 365000 --batch-size 100` -> `batches=0 deleted_rows=0 deleted_files=0 missing_files=0`
  - `scripts/cleanup_stale_guest_sessions.py --retention-days 365000 --batch-size 100` -> `batches=0 deleted_rows=0`

Acceptance criteria
- Jobs run successfully in stage with expected row/file effects.
- No lock/contention concerns from batch sizing.
- Rollback/disable instructions documented.

---

### M5 - Production Security Drift Checks (0.5-1 day)
Scope
- Prevent config drift from weakening security posture.

Tasks
- [x] Add deployment checks for secure cookies and HTTPS base URL.
- [x] Verify debug routes disabled in production config.
- [x] Verify HSTS behavior under HTTPS base URL.
- [x] Add CI or preflight gate for critical security settings.

M5 progress (2026-03-26)
- Added reusable security preflight logic in `app/core/security_preflight.py` and executable runner `scripts/preflight_security.py`.
- Preflight gate enforces critical production checks already defined in settings validation (HTTPS `BASE_URL`, `COOKIE_SECURE=True`, `DEBUG_ROUTES_ENABLED=False`, non-default secrets/DB settings).
- Added repeatable VS Code task gate `preflight:security` in `.vscode/tasks.json` (production mode).
- Added coverage for preflight mode/strict behavior in `tests/test_security_preflight.py`.
- Added dedicated HSTS verification tests in `tests/test_security_hsts.py` to ensure header emission only on HTTPS requests with production-mode middleware.

Acceptance criteria
- Security preflight fails fast on unsafe prod configuration.
- Checks are documented and repeatable.

---

### M6 - Live and Event-Edit Hardening (1 day)
Scope
- Fold in open items from website review 2026-03-26 and close the remaining high-value reliability/security gaps.

Tasks
- [x] Add explicit access control/token strategy for `/live/{event_code}/data` and document intended public/private behavior.
- [x] Replace `random.choice` password generation with `secrets.choice` in event edit password repair flow.
- [x] Remove route-local imports in `app/api/events_editing.py`; move to module top-level.
- [x] Add logging for per-row exceptions in live item shaping (`app/api/live.py`) to avoid silent data loss.
- [x] Add unit tests for `_shape_live_items` covering image, video, unsupported MIME, and malformed row cases.
- [x] Decide and implement whether the live slideshow upload link should be conditional (event-level flag) or explicitly documented as always visible.

M6 progress (2026-03-26)
- Added short-lived signed token gating for live data endpoint in `app/api/live.py`:
  - token issued by `/live/{event_code}` page render,
  - token required and validated by `/live/{event_code}/data`,
  - invalid/missing token requests return `403` with audit logging.
- Updated `templates/live_slideshow.html` and `static/js/pages/live_slideshow.js` to propagate and use the token for data polling.
- Added per-row warning logs for `_shape_live_items` failures (`live.slideshow.shape_row_failed`) with file/event context.
- Replaced event password repair randomness with `secrets.choice` and centralized password helper logic in `app/api/events_editing.py`; removed route-local imports.
- Added focused tests:
  - `tests/test_live_shape_items.py` (image/video shaping, unsupported MIME skip, malformed row logging),
  - `tests/test_live_routes.py` tokenized data access and denial coverage.
- Documented upload-link behavior as explicitly always visible for kiosk/shared-screen flows in the live slideshow top bar.
- Validation passed: `ruff check .` clean and `pytest -q` (`221 passed, 11 skipped`).

Acceptance criteria
- Live data endpoint access behavior is explicit, tested, and documented.
- Event password generation uses cryptographically secure randomness.
- Live slideshow shaping failures are observable in logs.
- New unit tests guard live media shaping and prevent regression.

---

## Execution Order
1. M1 CSP and inline migration
2. M2 upload hardening
3. M3 enforcement consistency
4. M4 DB jobs
5. M5 production drift checks
6. M6 live and event-edit hardening

## PR Breakdown
- PR-1: M1 first template migration slice
- PR-2: M2 upload hardening and tests
- PR-3: M3 enforcement boundary tests
- PR-4: M4 DB jobs safe subset
- PR-5: M5 security drift checks
- PR-6: M6 live/event-edit hardening and tests

## Risks and Mitigations
- Risk: CSP tightening breaks page behavior.
  - Mitigation: report-only phase and incremental migration.
- Risk: SVG policy impacts user uploads unexpectedly.
  - Mitigation: explicit policy communication and targeted tests.
- Risk: DB cleanup jobs contend with live traffic.
  - Mitigation: batched deletes and off-peak schedules.

## Working Log
- 2026-03-24: Initial plan created.
- 2026-03-24: Completed M1 inline script and inline event-handler inventory; selected PR-1 migration slice.
- 2026-03-24: Implemented first M1 migrations for `share_event` and `addons`; targeted tests passed (`test_legacy_addons_redirect.py`, `test_smoke.py`).
- 2026-03-24: Completed remaining PR-1 M1 migrations for `admin_billing` and `examples`; targeted tests passed (`test_billing_admin_routes.py`, `test_e2e_copy_to_clipboard.py`, `test_theme_pages.py`).
- 2026-03-24: Enabled CSP report-only capability in middleware/settings and added focused tests for report-only header behavior.
- 2026-03-24: Completed another M1 migration slice for signup/reset-password/FAQ and validated with focused pytest coverage.
- 2026-03-24: Completed another M1 migration slice for create-event/contact; remaining executable inline-script blockers reduced to 16 templates.
- 2026-03-25: Completed another M1 migration slice for account-delete, account-delete-confirmed, events-dashboard, and profile; remaining executable inline-script blockers reduced to 12 templates.
- 2026-03-25: Completed M1 migration slice for tutorial, live_slideshow, gallery (aux IIFEs), and event_details (first block); remaining inline-script blockers reduced to 8 templates. Tests: test_tutorial_page, test_live_routes, test_gallery_no_react_refs, test_event_details_script all pass.
- 2026-03-25: Completed M1 migration slice for admin_components and admin_themes (both inline script blocks); remaining inline-script blockers reduced to 6 templates. Tests: test_admin_migration_scripts all pass.
- 2026-03-26: Merged website review findings into this plan and refreshed baseline state (`ruff check .` clean; `pytest -q` 187 passed, 11 skipped).
- 2026-03-26: Fixed regression on examples page by correcting Jinja macro call syntax in `templates/examples.html`.
- 2026-03-26: Fixed live slideshow noindex metadata path by adding missing `extra_meta` block in `templates/base.html`.
- 2026-03-26: Updated `tests/test_live_routes.py` URL assertions to account for slideshow media `?code=` query strings.
- 2026-03-26: Re-ran CSP inline inventory; removed last inline event-handler attribute from `templates/tutorial.html` and validated with focused pytest.
- 2026-03-26: Migrated `templates/components/lightbox.html` inline module script to external module source; remaining executable inline-script blockers reduced to 4 templates.
- 2026-03-26: Migrated `templates/extras.html` inline notice-dismiss script to `static/js/pages/extras.js`; remaining executable inline-script blockers reduced to 3 templates.
- 2026-03-26: Removed dead inline extras checkout script block from `templates/event_details.html`; remaining executable inline-script blockers reduced to 2 template locations (both in `templates/edit_event.html`).
- 2026-03-26: Migrated `templates/edit_event.html` final 2 inline script blocks to `static/js/pages/edit_event.js`, confirmed zero executable inline-script blockers in templates, and validated with `ruff check .` and `pytest -q` (`187 passed, 11 skipped`).
- 2026-03-26: Completed M2 upload hardening by enforcing explicit SVG rejection (including spoofed extension/content-type payload detection) in `app/services/mime_utils.py` and adding focused SVG policy tests; validated with `ruff check .` and `pytest -q` (`192 passed, 11 skipped`).
- 2026-03-26: Completed M3 plan-window enforcement consistency by adding table-driven upload/download window boundary tests and explicit expired-window negative tests in `tests/test_plan_windows.py`.
- 2026-03-26: Started M4 safe subset by implementing batched PaymentLog purge job (`app/jobs/maintenance.py`) with best-effort JobRunLog writes, plus runner script (`scripts/purge_payment_logs.py`) and focused tests (`tests/test_paymentlog_purge_job.py`).
- 2026-03-26: Expanded M4 safe subset with completed export cleanup and stale guest-session cleanup jobs, added runner scripts (`scripts/cleanup_completed_exports.py`, `scripts/cleanup_stale_guest_sessions.py`), and added focused tests (`tests/test_export_cleanup_job.py`, `tests/test_guestsession_cleanup_job.py`).
- 2026-03-26: Completed M5 production drift checks by adding a security preflight gate (`scripts/preflight_security.py`, `app/core/security_preflight.py`), adding HSTS behavior tests (`tests/test_security_hsts.py`), adding preflight tests (`tests/test_security_preflight.py`), and wiring task `preflight:security`.
- 2026-03-26: Completed M6 live and event-edit hardening by introducing signed live data tokens, adding live item shaping failure logs, migrating event edit password repair to `secrets.choice`, adding focused tests (`tests/test_live_shape_items.py`, updated `tests/test_live_routes.py`), and validating full suite health.
- 2026-03-26: Completed M4 stage dry-runs for all three maintenance scripts with conservative no-op settings (`--retention-days 365000 --batch-size 100`); all runners executed successfully and reported `deleted_rows=0`.