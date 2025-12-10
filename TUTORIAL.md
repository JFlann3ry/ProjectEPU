# ProjectEPU Tutorial — How the site works

This tutorial walks through the product from both Host and Guest perspectives, explains how uploads and galleries work end‑to‑end, and gives you tips for troubleshooting.

If you’re setting up locally, see README.md for environment and run instructions first.

## Roles at a glance
- Host: Creates an event, customizes theme, shares a guest code/link, reviews uploads, manages the gallery.
- Guest: Visits a share link or enters a code to upload photos/videos and leave an optional message.

## Core concepts
- Event: The space where files and guest messages live. Each event has a guest code and shareable link.
- Upload: A photo or video a guest (or host) adds to an event. Stored under `storage/{userId}/{eventId}/`.
- Gallery: The host’s management view. Server‑rendered grid with selection and bulk actions (slideshow moved to dedicated Live page).
- Deleted: Soft‑deleted files are moved to a “Deleted” filter; restore or permanently delete later.
- Themes: Colors/typography/background frosting applied consistently across guest and host pages.

## Host flow — create, share, manage
1) Sign up/log in, then go to Events → Create Event.
   - Fill in basic details. A guest code and share link are generated automatically.
2) Share with guests:
   - Share the link (e.g., https://your-domain/e/ABC123) or the event code.
   - Optionally set a password on the event for private uploads.
3) Customize the look:
   - Go to the event’s Edit page. Choose a Theme or customize colors/fonts/background image.
   - Changes are applied consistently to the guest upload page and the public share page.
4) Review uploads in the Gallery:
   - Navigate to the Gallery for the event (server‑rendered, no React).
   - Use filters (All/Images/Videos/Favorites/Deleted) and infinite scroll (fetches in batches).
   - Select one or many items. Bulk actions: Delete/Restore, Download as ZIP, Add to Album (if enabled).
   - For display, use the dedicated Live Slideshow page (see below).
5) Handle removals safely:
   - Delete sends items to Deleted (soft delete). From there, you can Restore or Permanently delete.
   - Deleted view groups items by days remaining until permanent deletion (where configured).

## Guest flow — upload with code or link
1) Go to Guest Upload and enter the event code, or follow the host’s share link.
2) Fill optional details: email and display name; leave a guestbook message if enabled.
3) Select photos/videos via drag‑and‑drop or click/tap. Accepts common image/video types.
4) Agree to terms (checkbox), then Upload.
5) See Your uploads: a mini grid with filtering and selection; remove your own items if you change your mind.

## Gallery features — details
- Server‑rendered Jinja templates so pages are fast and consistent; ARIA roles and keyboard support included.
- Infinite scroll uses IntersectionObserver to fetch additional pages without UI jumps.
- Lightbox and slideshow work with both images and videos (video thumbs fall back gracefully).
- Selection supports scope‑wide select all/clear; bulk actions don’t spam toasts.
- Deleted view groups by days remaining; dates are shown; text fits without overlapping.
- Filters collapse to one row on desktop; ordinal index badges were removed for visual simplicity.

## Security & privacy
- CSRF protection on state‑changing POSTs (cookie + meta + hidden inputs).
- MIME and size validation; optional server‑side sniffing if python‑magic is installed.
- Session cookies are HTTPOnly; `Secure` enforced when BASE_URL is https.
- Rate limiting on sensitive forms; Redis can be enabled for shared limits across instances.

## Storage & files
- Files are saved under `storage/{userId}/{eventId}/`.
- Metadata (EXIF/video) is parsed best‑effort and stored in the DB for sorting and display.
- Duplicate detection helps avoid re‑ingesting identical files.

## Billing (optional)
- Plans can be purchased for higher limits. Stripe checkout session + webhook finalize purchases.
- Limits (uploads, storage, features) are enforced based on the assigned plan.

## Admin & operability
- Admin dashboards for users/events/stats and audit logs (admin‑only routes).
- Logs include `X-Request-ID` and key action audits (login/logout/guest upload/etc.).

## Live Slideshow (Display Mode)
- Open `/live/{code}` for an on-site projector or large screen.
- Keyboard: ←/→ navigate, Space play/pause, `+`/`-` adjust delay, Esc exit fullscreen.
- Fullscreen hides controls; HUD auto-hides when idle, respecting reduced motion settings.
- Polls for new uploads (rate-limited).
- Planned: password gate if the event uses a password; optional SSE/WebSocket updates.

## Troubleshooting
- "I can’t upload": Check MAX_UPLOAD_BYTES and allowed MIME prefixes; see server logs for errors.
- "Gallery missing items": Confirm filters aren’t hiding them (e.g., Favorites only); check Deleted.
- "Theme not applying": Verify ThemeID or custom settings on the event; reload the page (styles are cached).
- "Stripe webhook failing": Verify STRIPE_WEBHOOK_SECRET; inspect logs for signature errors.
- "CAPTCHA failing": Ensure CAPTCHA_SECRET is set and passed from the client form.

## Developer notes
- Use `db.get_db()` dependency for database access in routers.
- When adding POST actions, include CSRF token in templates and validate server‑side.
- Keep new routes ordered with existing conventions (don’t move static mounts or parameterized routes arbitrarily).
- Use VS Code tasks for install/lint/tests; run `lint+test (windows-safe)` before committing.

## See also
- README.md — setup, routes, and roadmap
- USER_JOURNEYS.md — detailed journeys and actions
- SECURITY.md — security guidelines
- TESTING.md — how tests are structured
