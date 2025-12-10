# User Journeys and Action Catalog

This document summarizes the current end-to-end user flows and everything a user can do in the app, based on the code in `app/api/*`, models, and templates. Use it to align product intent, spot gaps, and plan next iterations.

## Personas
- Visitor (Unauthenticated)
- Host (Registered/Logged-in User)
- Guest (Uploader with event code/password)
- Admin (IsAdmin = true)

---

## Visitor Journeys

1) Discover and access
- Visit `/` -> marketing homepage; shows dashboard CTA if logged in (no forced redirect)
- View `/login`, `/signup`, `/verify` (notice), `/terms`, `/billing` (pricing), `/contact`

2) Sign up and verify
- GET `/signup` -> sign_up.html
- POST `/auth/signup` with first/last/email/password
  - Validates basic password policy
  - Creates user (if email unique), sends verification email (if SMTP configured)
  - Shows `/verify_notice`
- GET `/verify-email?token=...` -> marks user as verified -> shows login page with success message

3) Log in
- GET `/login`
- POST `/auth/login` with email/password
  - In-memory rate limit by IP+email
  - Requires `EmailVerified = True`
  - Creates/rotates session cookie `session_id`
  - Redirects to `/profile`

---

## Host Journeys (Logged-in)

1) Profile & plan badge
- GET `/profile`
  - Shows active plan badge and features (best-effort lookup)
- GET `/profile/edit` -> edit_profile.html (CSRF-protected form; supports name updates and email change flow)
- GET `/logout` clears session; `/account/delete` allows deletion with confirmation (deactivates sessions, sends email)

2) Billing & plans
- GET `/billing` pricing page (Stripe publishable key injected)
- POST `/create-checkout-session` to start Stripe checkout
- POST `/stripe/webhook` updates purchases/logs on events
- After success, host returns to `/billing?success=1`

3) Events dashboard
- GET `/events` shows user’s events with plan badge and totals

4) Create event (plan enforcement)
- GET `/events/create`
  - Requires an active paid plan; redirects to `/billing` if missing
  - If on `single` plan, enforces one-event cap
- POST `/events/create`
  - Validates name and terms checkbox
  - Resolves/creates `EventType`
  - Generates unique 6-char event code
  - Creates event and redirects to `/events/{id}`

5) Event details & sharing
- GET `/events/{id}`
  - Shows event details, guest upload link `/guest/upload/{code}` and QR

6) Customize event
- GET `/events/{id}/edit` shows theme picker and customization fields
- POST `/events/{id}/edit` updates name/date/password/theme & colors; validates and stores logo/banner assets (MIME + size checks); persists customization

7) Gallery management (server-rendered)
- GET `/gallery` (across events, with optional signed cookie scoping) and `/events/{id}/gallery`
  - Filters: images/videos, favorites-only, album filter, show deleted
  - Deterministic pagination with `offset` and `limit`, tie-breaker by FileMetadataID
- POST `/gallery/actions/delete` or `/gallery/actions/restore` (CSRF-validated; skips CSRF for TestClient)
- POST `/gallery/download-zip` -> builds a zip of selected items (capped by plan feature `max_zip_download_items` if configured)
- Favorites: POST `/gallery/favorite` and `/gallery/unfavorite`
- Albums:
  - GET `/events/{event_id}/albums` (owner list for selector)
  - POST `/events/{event_id}/albums/create`
  - POST `/events/{event_id}/albums/{album_id}/add` and `/remove`

---

## Guest Journeys

1) Access event
- GET `/guest/login` -> submit event code (and optional event password)
- POST `/guest/login` -> redirects to `/guest/upload/{code}` on success

2) Upload media
- GET `/guest/upload/{code}` -> shows upload form themed via event customization
- POST `/guest/upload/{code}` with files + optional email/device + terms
  - Validates server-side content (MIME prefixes) and per-file size
  - Enforces guest cap per event if plan feature `max_guests_per_event` set (distinct guest emails)
  - Stores files under `storage/{userId}/{eventId}/` with collision-safe names
  - Extracts metadata (image/video) best-effort; persists `FileMetadata`
  - Generates thumbnails/posters when possible for fast gallery loads

---

## Admin Journeys

1) Dashboard & insights
- GET `/admin` (IsAdmin only)
  - Stats: users, events, files, purchases, total storage (best-effort)
  - Top events by upload count
  - Recent signups (latest 10) and uploads (latest 10)
  - Recent error lines tailed from logs
  - Search (q) across users and events
  - Link to errors page `/admin/errors` with filters for request_id and date window
  
2) Errors page
- GET `/admin/errors` (IsAdmin only) — paginated AppErrorLog view with request_id/since/until filters

3) Mini-dashboard
- GET `/admin/mini-dashboard` (IsAdmin only)
  - Shows recent AppErrorLog rows and recent delete/restore action logs
  - Reveals debug routes link only if `DEBUG_ROUTES_ENABLED` is true

2) Billing views
- GET `/admin/billing` -> text list of recent purchases
- GET `/admin/payment-logs` -> text list of payment logs

3) Audit logs export
- GET `/admin/audit-logs` -> downloads main log file (best-effort)

---

## Support
- GET `/contact` -> contact form
- POST `/contact` -> sends email to support inbox (if configured), with IP-based rate limiting and optional CAPTCHA token presence check

---

## Action Catalog (Routes)

Auth & Account
- GET `/login` | POST `/auth/login`
- GET `/signup` | POST `/auth/signup`
- GET `/verify-email?token=` | GET `/verify` (notice) | GET `/verify-notice`
- GET `/logout`
- GET `/account/delete` | POST `/account/delete`

Profile
- GET `/profile` | GET `/profile/edit`

Events
- GET `/events` | GET `/events/create` | POST `/events/create`
- GET `/events/{id}` | GET `/events/{id}/edit` | POST `/events/{id}/edit`

Gallery
- GET `/gallery` | GET `/events/{id}/gallery` | GET `/gallery/data`
- POST `/gallery/actions/delete` | POST `/gallery/actions/restore` | POST `/gallery/actions/permadelete`
- POST `/gallery/download-zip`
- POST `/gallery/favorite` | POST `/gallery/unfavorite`

Guest
- GET `/guest/login` | POST `/guest/login`
- GET `/guest/upload/{code}` | POST `/guest/upload/{code}`

Billing/Plans
- GET `/billing`
- POST `/create-checkout-session`
- POST `/stripe/webhook`
- GET `/admin/billing` (admin)
- GET `/admin/payment-logs` (admin)

Admin & Support
- GET `/admin` (admin) | GET `/admin/errors` (admin) | GET `/admin/mini-dashboard` (admin)
- GET `/admin/audit-logs` (admin) | GET `/admin/audit-logs/export` (admin)
- GET `/contact` | POST `/contact`
  
Debug (gated by settings.DEBUG_ROUTES_ENABLED)
- POST `/gallery/actions/delete-debug` (user; non-mutating)
- GET `/debug/gallery/delete_logs` (admin)

Misc
- GET `/` (redirect) | GET `/terms` | GET `/health` | GET `/health.txt` | GET `/qr`

---

## Constraints & Validations (Key)
- Auth
  - Login rate-limited (in-memory) by IP+email
  - Session cookie `session_id` HttpOnly; `Secure` if BASE_URL is https
  - Email must be verified to log in
- Plans & Limits
  - Creating events requires an active paid plan
  - `single` plan limits to one event per user
  - `max_guests_per_event` enforced by distinct `GuestSession.GuestEmail`
  - `max_zip_download_items` caps bulk downloads
- Uploads
  - MIME prefix validation (server-side sniffing if python-magic installed)
  - Per-file size limit via `MAX_UPLOAD_BYTES`
  - Optional event storage cap via `EventCustomisation.StorageLimitMessage` (interpreted as MB)
- Admin
  - Access gated by `Users.IsAdmin`
  - Log tailing best-effort
  - AppErrorLog writes for 404/HTTPException/500 with `X-Request-ID` propagation
- Support
  - Rate-limited per client IP; optional CAPTCHA token presence when configured

---

## Known Gaps & Opportunities
- Security
  - CSRF now implemented on key forms (gallery actions, profile edit, owner upload), but coverage not universal
  - No real CAPTCHA verification yet (presence check only); consider hCaptcha/Turnstile
  - Event passwords stored plaintext (consider hashing)
  - `/storage` is mounted publicly; consider signed/authenticated URLs for prod
  - In-memory rate limiting not shared across instances; use Redis
- UX / Product
  - Profile edit saving flow is minimal (add fields & save route)
  - Admin users view exists (`/admin/users`) with filters/pagination; ensure links from dashboard
  - No admin UI to manage `IsAdmin` roles from dashboard; exists via `/admin/users/{id}/set-admin`
  - Add gallery modal a11y parity complete (delete + create-album); consider tests for keyboard trap
- Billing
  - No admin refund/cancel flows; limited webhook resilience
- Observability
  - Sentry performance tracing disabled by default; limited error context
  - AppErrorLog persisted for 404, HTTPException, and 500
- Tests
  - Expand pytest coverage for auth, upload edge cases, and billing webhook logic
  - Optional Playwright E2E can validate gallery delete/restore/upload flows; currently opt-in

---

## Missing bits and what needs sorting

Prioritized list:

1) Security hardening
  - Expand CSRF coverage to all mutating endpoints (albums add/remove/create, event edits with JSON, admin actions)
  - Replace plaintext event passwords with hashed storage; add migration + compatibility window
  - Add production-grade rate limiting (Redis) and per-user limits on sensitive routes
  - Introduce real CAPTCHA for contact/guest flows; wire keys via settings

2) Gallery completeness
  - Owner upload entry point on gallery pages (button already posts to `/events/{id}/upload`)—document and ensure visibility when scoped by cookie
  - Album selection UX: Add-create modal integrated with server endpoint; add tests for album add/remove
  - ZIP download: add size/time guards and background-job fallback for large sets

3) Admin UX
  - Link admin dashboard cards to `/admin/users` and `/admin/errors` detail pages
  - Add user/event detail pages; enable role management from dashboard
  - Add pagination to top lists and search results

4) Billing resiliency
  - Add admin refund/cancel flows and improve webhook idempotency reporting
  - Display plan features on `/billing` and surface caps (zip items, guests/event) in UI

5) A11y & UX polish
  - Extend keyboard tests for all modals (including shared modal in `base.html`)
  - Verify focus restoration after gallery lightbox and album flows in tests

6) Observability
  - Enable Sentry traces in staging with low sample rate; add request-id propagation to client errors
  - Consider structured audit logs for gallery actions (beyond in-memory diagnostics)

7) Docs
  - README: add admin routes index and note about DEBUG_ROUTES_ENABLED
  - MIGRATIONS: include example for hashing event passwords migration

---

## Notes
- Email sending is a no-op if credentials are not configured; verification flow still functions via token check
- Large uploads may need server settings tuned (Uvicorn/Starlette limits)
