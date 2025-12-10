# Website Backlog — ProjectEPU

This is a living checklist of improvements and follow‑ups for the current website. Items are grouped and prioritized. Use checkboxes to track progress; keep diffs small and align with PERMANENT_INSTRUCTIONS.

Legend: [P0] critical, [P1] important, [P2] nice‑to‑have

## Live Gallery Slideshow [new]
- [ ] [P0] Password‑protected events: require password entry on `/live/{code}` when the event has a password (mirror guest login behavior; cache session in cookie).
- [ ] [P0] Add basic rate limiting to `/live/{code}/data` (reuse existing limiter; document keys in `REDIS_USAGE.md`).
- [ ] [P1] Improve HUD UX: auto‑hide controls after inactivity; keep keyboard/focus accessible; ensure focus ring is visible on dark UI.
- [ ] [P1] “Reduced motion” support: disable transitions/animations when `prefers-reduced-motion: reduce`.
- [ ] [P1] Preload next slide (image) to reduce perceived delay; clamp polling when the tab is hidden.
- [ ] [P1] Error handling: offline indicator and exponential backoff for fetch failures.
- [ ] [P1] Optional faster updates via SSE/WebSocket when Redis is available (fallback to polling).
- [ ] [P2] Configurable transitions (fade, slide) and per‑event default delay.
- [ ] [P2] Add “Now playing” metadata (filename/time) with a toggle in HUD.

## Gallery (host management)
- [x] [P0] Replace “Play Slideshow” with a CTA to the dedicated Live Slideshow.
- [ ] [P1] Remove dead slideshow code paths in `static/js/pages/gallery.js` and tidy related CSS.
- [ ] [P1] Add “Open Live Slideshow” CTA on `event_details.html` (carry `event.Code`).
- [ ] [P2] In-gallery toast linking to `/live/{code}` when new files arrive (optional prompt for on‑site display).

## Extras and Entitlements
- [ ] [P1] Decide gating: if Live Gallery is a paid extra, gate `/live/{code}` when entitlement is missing; show upsell banner or redirect to Extras with `event_code`.
- [ ] [P1] From `extras_detail.html` (Live Gallery), add a “Launch Live Slideshow” button when an `event_code` is present.

## Accessibility (site‑wide)
- [ ] [P0] Audit color contrast on dark backgrounds (live page HUD, modals); fix any < 4.5:1.
- [ ] [P1] Ensure all interactive elements have clear focus states and accessible names (aria‑labels where needed).
- [ ] [P1] Validate landmarks and roles on new pages (e.g., `/live` uses a sensible landmark structure).

## SEO and Open Graph
- [ ] [P1] Add `<meta name="robots" content="noindex">` to `/live/{code}` and other ephemeral pages.
- [ ] [P2] Expand canonical tags and OG/Twitter metadata for key marketing pages (pricing, extras details).
- [ ] [P2] Generate/update sitemap to include new SSR routes as needed (exclude `/live`).

## Performance
- [ ] [P1] Tune caching headers for `/thumbs/{id}.jpg` and `/live/{code}/data` (short max‑age with ETag/Last‑Modified where possible).
- [ ] [P1] Consider `preconnect` to storage/static and font hosts; verify compression middleware coverage for new routes.
- [ ] [P2] Lazy‑load noncritical images on content pages and cap hero image sizes.

## Security & Hardening
- [ ] [P0] CSP/Referrer‑Policy review (apply strict defaults site‑wide; allowlist necessary origins only).
- [ ] [P1] Confirm CSRF not required for GET routes; ensure all POSTs include validation and continue TestClient bypass in tests.
- [ ] [P1] Validate error logging for 4xx/5xx still captures `X-Request-ID` for `/live` paths.

## Tests
- [ ] [P0] Add unit/integration tests:
  - `/live/{code}`: 404 for unknown/unpublished; 200 for published.
  - `/live/{code}/data`: returns only non‑deleted items; respects `since`; caps `limit`.
  - Cookie‑scoped gallery page includes `event_code` in context and shows CTA.
- [ ] [P1] Smoke test for Extras checkout step‑of‑10 remains enforced after recent changes.
- [ ] [P1] Accessibility smoke (Playwright): tab order and focus visibility on live HUD.

## Docs & Content
- [ ] [P1] Update `TUTORIAL.md` and `README.md` to reference the dedicated Live Slideshow (remove “start slideshow from lightbox” guidance).
- [x] [P1] Update FAQ answer about slideshows to point to `/live/{code}`.
- [ ] [P1] Add a short “Live Slideshow” section to the marketing site (What it does, where to find it).

## Ops & Observability
- [ ] [P2] Add structured logs for slideshow play/pause/next/prev (client beacons or server counts) with sampling.
- [ ] [P2] Basic uptime check for `/` and `/live/FAKE` 404 response shape.

---

Housekeeping
- [ ] Keep diffs minimal; preserve logging context and route order.
- [ ] Run Ruff and Pytest before merging; if schema changes, add Alembic revision and upgrade locally.
