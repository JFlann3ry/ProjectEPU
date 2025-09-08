# <Project Name> — Roadmap Template

A pragmatic template to plan and ship product increments in clear phases with checklists, acceptance criteria, and operational readiness.

Last updated: 2025-08-20
Owner: <Name / Team>

---

## How to use this template
- Make a copy of this file as `ROADMAP.md` (or keep per workspace).
- Fill in placeholders (<>), drop any sections that don’t apply.
- Keep items small, verifiable, and testable.
- For each phase/MVP: list “Goal”, “Build” (checklist), and “Acceptance”.
- Prefer short weekly increments; update status with [x] when done.

---

## 1) Overview
- Problem statement: <What problem are we solving?>
- Users / audiences: <Who benefits?>
- Outcomes: <Top 3 measurable outcomes>
- Non-goals: <What we won’t do now>

## 2) Success metrics
- Activation / conversion: <e.g., % signup->first action>
- Performance / reliability: <e.g., p95 latency, error rate>
- Ops: <e.g., on-call tickets/month>
- Business: <e.g., paid conversions, retention>

## 3) Constraints and assumptions
- Tech constraints: <e.g., DB, runtime, licensing>
- Regulatory/compliance: <e.g., GDPR, PCI scope>
- Data residency / PII: <e.g., storage locations>
- Budget/time constraints: <e.g., headcount, deadline>

## 4) Architecture snapshot (high-level)
- Backend: <frameworks/languages>
- Frontend: <frameworks/languages>
- Storage/DB: <DBs, blob storage>
- Integrations: <payments, email, auth, analytics>
- Deployment: <containers, systemd, cloud>
- Observability: <logs, traces, metrics>

---

## 5) Phased plan

### Phase 0 — Stabilize and Unify (Foundation)
Goal
- Single-source configuration and consistent app skeleton.

Status: Done ✅

Build
- [x] Centralized settings (.env + typed settings).
- [x] Shared DB/session dependency; remove ad-hoc engines.
- [x] Core middlewares (request ID, structured logging, error handlers).
- [x] Basic security defaults (cookies, upload validation, safe filenames).
- [x] Static/UI baseline; header/footer consistency.

Acceptance
- App boots cleanly; main routes reachable.
- Logs carry request IDs; 404/500 show friendly pages.

---

### MVP 1 — Accounts & Sessions
Goal
- Users sign up, verify, log in/out; protected pages.

Status: Done ✅

Build
- [x] Signup + password policy; unique email.
- [x] Email verification (dev no-op OK).
- [x] Login with rate limiting.
- [x] Session create/get/deactivate; rotation on login; expiry enforced.

Acceptance
- New user can complete full auth flow.
- Protected pages are gated when logged out.

---

### MVP 2 — Core Object Creation & Guest Actions
Goal
- Event creation and guest upload/share flows.

Status: Done ✅

Build
- [x] Create Event with human-friendly code.
- [x] Details/share page with shareable link and QR.
- [x] Guest access (code-based; password optional).
- [x] Upload flow with metadata capture (e.g., email, device type, file type/size, checksum).

Acceptance
- Host creates event; guest uploads files; data and metadata persisted.

---

### MVP 3 — Management & Gallery/List
Goal
- Owners can browse, filter, download/export, soft-delete/restore.

Status: In progress (3/4) ⏳

Build
- [ ] Grid/list with filters (type/date/search).
- [x] Lightbox/slideshow or detail view.
- [x] Zip/bulk export.
- [x] Soft delete + restore.

Acceptance
- Uploaded/created items are visible and manageable.

---

### MVP 4 — Themes/Customization (Optional)
Goal
- Visual customization for main/guest pages.

Status: Done ✅

Build
- [x] Seed themes; customization model.
- [x] Edit page with live preview; save.
- [x] Apply theme to primary/guest flows.

Acceptance
- Selecting a theme updates UI and persists.

---

### MVP 5 — Monetization (Plans/Payments) (Optional)
Goal
- Paid plans unlock higher limits/features.

Status: In progress (2/3) ⏳

Build
- [x] Pricing page + checkout session (e.g., Stripe).
- [x] Webhook: mark purchase complete; assign plan.
- [ ] Enforce plan limits (e.g., count caps, storage, downloads).

Acceptance
- Purchase recorded; limits applied in key routes.

---

### MVP 6 — Admin & Support
Goal
- Operability, moderation, and support.

Status: Done ✅

Build
- [x] Admin dashboard: users, objects, usage stats.
- [x] Audit logs for key actions; export.
- [x] Basic support/contact flow.

Acceptance
- Admin can inspect system health and answer user issues.

---

Follow-ups (near-term)
- [ ] Gallery filters: finalize server-side filtering/pagination for type/date/search.
- [ ] Plan limits enforcement: apply per-plan caps (items, storage, downloads).
- [ ] Terms/Privacy pages: create content and routes.
- [ ] Type checks: enable mypy/pyright baseline and fix violations.
- [ ] Pre-commit hooks: run Black/Ruff (and optional isort) on commit.
- [ ] Observability: enable Sentry/OTel traces in prod (optional, gated by env).
- [ ] Backups: automate DB and storage backups; document restore steps.

---

### MVP 7 — Public Gallery Controls & Watermarking
Goal
- Safer sharing with host-controlled access and branding.

Status: Planned 📝

Build
- [ ] Public, view-only gallery mode (toggle per event).
- [ ] Optional passcode on share links; link expiration.
- [ ] Watermark on downloaded images (event name/logo); size/quality caps.
- [ ] Host switches to disable downloads and/or hide originals.

Acceptance
- Host shares a public link; guests can view gallery; configured controls (passcode/download) are enforced and watermarks appear on downloads.

---

### MVP 8 — Moderation & Safety
Goal
- Keep content safe and give hosts tools to manage reports.

Status: Planned 📝

Build
- [ ] Basic NSFW/unsafe detection pipeline (flag to quarantine queue).
- [ ] Guest “Report” action; reason capture; notify host.
- [ ] Moderation queue: approve/restore, delete, bulk actions.
- [ ] Audit log entries for moderation actions.
- [ ] Blocklist by email/device hash on repeated violations.

Acceptance
- Flagged uploads are quarantined by default; host can approve/deny with actions recorded; reported content not visible publicly until approved.

---

### MVP 9 — Notifications & Messaging
Goal
- Keep hosts informed and acknowledge contributors.

Status: Planned 📝

Build
- [ ] Host notifications: immediate or daily digest of new uploads.
- [ ] Optional guest confirmation/thank-you email with share link.
- [ ] Outbound webhook for new upload (Slack/Teams via webhook URL).
- [ ] Pluggable email provider config (dev: console; prod: SMTP/API).

Acceptance
- In dev, emails/logs appear in console; in prod, real emails/webhooks deliver; toggles per event control which notifications are sent.

---

### MVP 10 — Analytics & Insights
Goal
- Visibility into engagement, contributions, and storage.

Status: Planned 📝

Build
- [ ] Event dashboard metrics: uploads by day, active guests, favorites.
- [ ] Top contributors list; per-guest counts.
- [ ] Storage usage per event and per file type; cost estimate (if enabled).
- [ ] Export CSV of uploads/metadata.

Acceptance
- Host can view metrics with real event data and export a CSV that matches what’s shown.

---

### MVP 11 — Mobile/PWA & Resumable Uploads
Goal
- Reliable mobile experience and large-file uploads.

Status: Planned 📝

Build
- [ ] PWA install (manifest + service worker); app icon and splash.
- [ ] QR code “Join event” deep link flow.
- [ ] Chunked/resumable uploads (e.g., tus protocol or S3 multipart proxy).
- [ ] Background retry on flaky networks; progress persistence.

Acceptance
- On mobile, users can install to home screen; large uploads resume after network interruption and complete successfully.

---

### MVP 12 — Integrations & Extensibility
Goal
- Open ecosystem for storage, delivery, and automation.

Status: Planned 📝

Build
- [ ] Pluggable storage backends (local, S3, Azure Blob); CDN option.
- [ ] Public REST API (minimal): events CRUD (host), upload create (guest), file list (host).
- [ ] Outbound webhooks with signing secret for key events (upload completed, favorite added).
- [ ] API keys management (scoped, revocation); rate limiting.

Acceptance
- Storage can be switched via config; CDN serves public assets; API and webhooks work with sample clients and verify signature.

---

Future candidates
- Billing expansion: coupons/trials, invoices, taxes/VAT, overage handling.
- White-label & custom domains per host; remove platform branding.
- AI-assisted curation: auto-tagging, face clustering, highlight reel.
- Compliance & retention: data export/delete (GDPR), retention policies.
- Internationalization: i18n/l10n, multiple currencies, date formats.

## 6) Engineering enablers
- Migrations
  - [x] Alembic/Flyway: initial schema + upgrades; CI check.
- Testing
  - [x] pytest or equivalent; smoke + happy path + 1–2 edge cases per route.
  - [x] Unit tests for parsing/validation helpers.
- Tooling & quality
  - [x] Formatter + linter (Black/Ruff/ESLint/etc.).
  - [ ] Pre-commit hooks.
  - [ ] Type checks (mypy/pyright/tsc where practical).
- Security
  - [x] Minimal threat model; input validation; safe file handling.
  - [x] Secrets handling (.env, managers, rotation notes).
- Observability
  - [x] Structured logs; health endpoints.
  - [ ] Optional: Sentry/OTel traces and error reporting.
- Deployment
  - [x] Dockerfile or systemd + reverse proxy.
  - [ ] Environment provisioning; backups (DB + storage).

## 7) Operational readiness
- SLOs: <latency/availability targets>
- Alerts: <what to alert and thresholds>
- Runbooks: <top 5 incidents and steps>
- Backups/restore: <frequency and test>

## 8) Risks & mitigations
- <Risk 1> — Mitigation: <...>
- <Risk 2> — Mitigation: <...>
- <Risk 3> — Mitigation: <...>

## 9) Timeline (example)
- Week 1–2: Phase 0
- Week 3–4: MVP 1
- Week 5–6: MVP 2
- Week 7–8: MVP 3
- Week 9: MVP 4 (optional)
- Week 10: MVP 5 (optional)
- Week 11: MVP 6 / hardening

Adjust based on scope and resourcing. Track slip factors and buffer.

## 10) Route coverage checklist (example)
- [x] GET /
- [x] GET /login; POST /auth/login
- [x] GET /signup; POST /auth/signup
- [x] GET /verify
- [x] GET /logout
- [x] GET /profile; GET /profile/edit
- [x] GET /objects; GET/POST /objects/create; GET /objects/{id}; GET/POST /objects/{id}/edit
- [x] GET /guest/login; GET/POST /guest/action/{code}
- [x] GET /gallery
- [x] GET /billing (if monetization)
- [ ] GET /terms /privacy
- [x] GET /health /health.txt

## 11) Quality gates (green-before-done)
- Build: PASS
- Lint/Typecheck: PASS
- Unit tests: PASS
- Smoke test critical paths: PASS

## 12) Definition of Done
- Functionality complete with tests.
- Docs updated (README/ROADMAP/CHANGELOG).
- Security and logging reviewed.
- Migrations applied and verified.
- Deployed to target environment.

## 13) Open questions
- <Open question 1>
- <Open question 2>
- <Open question 3>

## 14) Appendix
- Links: <Design docs, tickets, dashboards>
- Glossary: <Domain terms>
- Change log: keep diffs per milestone.
