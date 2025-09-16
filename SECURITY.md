# Security Guide

Quick reference for security settings and recommended controls.

## Cookies & sessions
- Set `HttpOnly` and `SameSite=Lax` on session cookies. Use `Secure` in production (https).
- Rotate session IDs on login.

## CSP & inline JS
- Plan to migrate inline JS to `static/js/` modules and enable a CSP without `unsafe-inline`.

## Secrets
- Do not commit secrets. Use `.env` locally and a secrets manager in production.

## Uploads
- Validate MIME types server-side and limit file sizes. Sanitize filenames.

## Webhooks
- Verify Stripe webhook signatures using `STRIPE_WEBHOOK_SECRET`.

## Monitoring
- Enable Sentry (optional) for error reporting; mask PII where possible.
