# Security Guide

Quick reference for security settings and recommended controls.

## Cookies & sessions
- Set `HttpOnly` and `SameSite=Lax` on session cookies. Use `Secure` in production (https).
- Rotate session IDs on login.
- Production startup now fails fast when unsafe defaults are detected (`ENV=prod` or `APP_ENV=prod`), including default `SECRET_KEY`, non-HTTPS `BASE_URL`, `COOKIE_SECURE=false`, or `DEBUG_ROUTES_ENABLED=true`.
- Use the explicit preflight gate before deployment to catch the same issues without starting the app:

```powershell
venv\Scripts\python.exe scripts\preflight_security.py --mode production
```

## CSP & inline JS
- Plan to migrate inline JS to `static/js/` modules and enable a CSP without `unsafe-inline`.
- Security headers are applied by `SecurityHeadersMiddleware` on HTML responses (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`).
- `Strict-Transport-Security` is emitted when running with an HTTPS base URL.
- CSP report-only support is available via `CSP_REPORT_ONLY` and `CSP_REPORT_URI` for staged rollouts.

## Secrets
- Do not commit secrets. Use `.env` locally and a secrets manager in production.

## Uploads
- Validate MIME types server-side and limit file sizes. Sanitize filenames.
- Owner and guest uploads are now spooled to temp files and rejected as soon as they exceed configured size limits, which keeps request memory bounded during large uploads.
- SVG uploads are explicitly rejected, including spoofed content-type/extension attempts when payload sniffing identifies SVG content.
- Raw originals are no longer served from a public `/storage/` mount. Media now flows through `/media/{user_id}/{event_id}/{filename}` with owner-session, guest-cookie, or published-event code checks, and nginx denies direct `/storage/` access.

## Live slideshow
- `/live/{event_code}` remains a published-event view, but `/live/{event_code}/data` now requires a short-lived signed token minted by the page render.
- Invalid or missing live-data tokens are denied with `403` and audit logging.
- Live item shaping failures are logged per row (`live.slideshow.shape_row_failed`) to avoid silent media loss.

## Webhooks
- Verify Stripe webhook signatures using `STRIPE_WEBHOOK_SECRET`.

## Monitoring
- Enable Sentry (optional) for error reporting; mask PII where possible.
- Contact support email delivery failures are logged to `audit` and persisted to `AppErrorLog` with `RequestID` for operator triage.
