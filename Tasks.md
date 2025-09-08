### 
## Goal
- 

## Build -  Here you suggest what needs building with tick off boxes like the example
- [ ] Example

## Acceptance
- 
==========================================
### Footer
## Goal
- Remove the time and just have the year

## Build -  Here you suggest what needs building with tick off boxes like the example
- [x] Update `templates/base.html` footer to render only the current year (e.g., `now().strftime('%Y')`).
- [x] Ensure `now` is available in Jinja globals; fall back gracefully if missing.
- [x] Remove any client-side time display logic (none expected).
- [x] Add a quick smoke test: render a simple page and assert the footer matches `/©\s*\d{4}\s*EPU/`.

## Acceptance
- [x] Footer shows © YEAR EPU with no time component (e.g., `© 2025 EPU`).
# Work Plan

## Sitewide layout consistency
### Goal
- Center page heroes and primary content; unify card widths/heights.

### Build
- [x] Add container max-width variable (already in CSS as `--container`); ensure `.container.center { margin: 0 auto; }` is applied across pages.
- [x] Standardize page hero: ensure `.page-hero.center` on all pages with titles/subtitles.
 - [x] Normalize grid helpers: prefer `.grid-2.equal-heights` with `align-items: stretch` (pricing, home features, admin dashboard, examples).
- [x] Ensure cards in grids use `.card.full-height` where appropriate. (Applied to Events Dashboard, Admin Dashboard, Admin Event.)
- [ ] Visual QA checklist for top-level pages (Home, Pricing, Events, Gallery, Upload, Auth, Profile, Admin, Contact, Terms).

### Acceptance
- [x] Event Details, Contact, Terms, Profile, Upload, and Auth pages have centered hero and content. (Contact, Terms, Profile updated; Home/Pricing/Examples/Admin now consistent.)
- [x] Two-column pages have equal-height cards and clean alignment. (Admin pages, Pricing hero grid, and other grids updated.)

==================================================

### Terms & Conditions Page /terms
## Goals
1) Fix the title centering to match all other pages.
2) Beef up the terms and conditions to help us be more legally compliant.

## Build
- [x] Apply `.page-hero.center` to the `/terms` template.
- [x] Create partial `templates/components/terms_text.html` with robust sections (definitions, usage, content rights, takedown, privacy, DMCA/GDPR notices, plan limits, prohibited content, liability, disclaimers).
- [x] Create `GET /terms/embed` that returns the partial only (for modal use; no layout).
- [x] Wire guest upload modal to fetch `/terms/embed` into a scrollable div.
- [x] Add a “Last updated” date variable and render in both full page and embed. (Set in code as `TERMS_LAST_UPDATED`.)

## Acceptance
- [x] Title/subtitle centered; page matches global layout.
- [x] Terms content is expanded and reused by the modal via `/terms/embed`.

==================================================

### Contact Support /contact
## Goals
1) Fix title centering
2) Button text centering to match other forms
3) Fix text box sizing
4) Order the Topics in alphabetical order apart from Other at the bottom
5) Topics options
6) Add sensible Character Limits
7) Add placeholder text in the “How can we help?” section
8) Increase the size of the “How can we help?” text box
9) Invalid form token error
10) A better thanks-for-contacting page

## Build
- [x] Center hero (`.page-hero.center`) and card (`.card.center`).
- [x] Submit button uses `btn primary block`; text centered consistently.
- [x] Textarea: readable contrast, min-height ~8 lines, vertical resize only.
- [x] Topic select: sort A–Z with “Other” last; values: Account, Billing, Feature request, Abuse/report, Technical issue, Data/privacy, Event help, Other.
- [x] Conditional fields: on Topic=Billing show “Order number” and “Event URL” (optional).
- [x] Char limits + counters: Name (80), Email (254 with RFC), Subject (when Topic=Other) (120), Message (2000).
- [x] Placeholders: contextual examples per topic; update on change.
- [x] CSRF: GET sets cookie; template includes token; POST validates; on failure, preserve state and show inline error.
- [x] Success page `/contact/sent` with compact confirmation; use PRG (redirect after POST).
- [x] Rate limit (IP/session) and honeypot field to reduce spam.
- [x] Email body includes Topic and extra fields.

## Acceptance
- [x] Title/button centered and consistent with other forms.
- [x] Topics sorted; “Other” reveals Subject.
- [x] Limits enforced and visible; textarea ~8 lines with scroll as needed.
- [x] No CSRF surprises on normal flow; successful POST redirects to thank-you page.

==================================================

### My Events /events
## Goal
- Improve the event card; remove the guest code from the card but keep the Share button.

## Build
- [x] Redesign card (v4) with richer banner, date tile, metrics, and quick actions (View, Gallery, Share, Edit).
- [x] Remove guest code display from the card.
- [x] Equal height cards; consistent padding/shadow.
- [x] Hover and focus states; keyboard navigable.
- [x] “Create event” button aligned with header; disable with tooltip when plan cap reached.
- [x] Add Published/Draft and Locked pills in header banner.

## Acceptance
- [x] Cards are visually consistent and actions aligned across rows.



==================================================

### Your Profile /profile
## Goal
1) Center title and text just below
2) Change the logout button
3) Make “Choose a plan” look like a link (clear affordance)
4) Email preferences modal
5) Billing link should go to a purchases summary

## Build
- [x] Center hero and card.
- [x] Logout button uses `btn danger`; confirm modal on click.
- [x] “Choose a plan” styled as prominent link (accent + underline on hover).
- [x] Email preferences modal: open from Profile; checkboxes; POST with CSRF; snackbar on success.
- [x] Billing summary page `/billing` (history of purchases, plans, add-ons; links to manage).

## Acceptance
- [x] Visual consistency achieved; email prefs edited in modal; billing goes to summary/history page.

==================================================

### Edit Profile /profile/edit
## Goal
1) Titles and text match other pages
2) Change reset password to a new page rather than display here
3) Email change should not be allowed
4) Suggest additional features

## Build
- [x] Center hero and card; show non-editable email field.
- [x] Replace inline password form with link to `/profile/password`.
- [x] Implement `/profile/password`: New + Confirm; CSRF; POST → send confirmation email with token link; complete on confirm.
- [x] “Download my data” (GDPR): request button, export job, status, and download; expires after 7 days. Manifest JSON only (no binary media).

## Acceptance
- [x] Email visible but read-only; password reset is a dedicated page with email confirmation.

==================================================

### Landing Page
## Goal
- Improve the layout; make it look nicer.

## Build
- [x] Hero with headline, subtext, and CTA buttons; centered.
- [x] Benefits section (3–4 columns) with icons.
- [x] How it works (3 steps with small visuals).
- [x] Testimonials placeholder.
- [x] Footer links to Terms, Contact, Privacy.

## Acceptance
- [x] Modern, tidy layout with consistent spacing and CTAs.

==================================================

### /examples
## Goal
1) Remove random “Create event” button at bottom
2) Add a link to each example to show what it could look like

## Build
- [x] Remove stray create button from template.
- [x] Each example card links to a demo page or screenshot modal. (Added "Preview" buttons opening lightbox.)

## Acceptance
- [x] No stray button; examples link to demos/previews.

==================================================

### FAQ Page
## Goal
- FAQs on their own page with expanding panels.

## Build
- [x] Create `/faq` page with accordion component.
- [x] Seed top 8–12 questions (uploading, supported formats, limits, privacy, refunds, contact).
- [x] Link footer to FAQ.

## Acceptance
- [x] FAQ page exists; panels expand/collapse; styling matches theme.

==================================================

### About Us
## Goal
- Add an About Us page.

## Build
- [x] Create `/about` with team placeholders, mission, and values.
- [x] Include contact CTA.

## Acceptance
- [x] About page matches site style; content is ready for copy.

==================================================

### Tutorial Page
## Goal
- A tutorial page that shows each step.

## Build
- [x] Create `/tutorial` with step-by-step cards: find event code, login, agree to terms, select/drag files, upload, view.
- [x] Add screenshots placeholders and short captions.

## Acceptance
- [x] Clear steps illustrated; links jump to relevant pages.

==================================================

### /guest/upload/
## Goal
- Add the option to leave messages for the guest when they upload.

## Build
- [x] DB: add GuestMessage model (EventID, GuestSessionID, DisplayName optional, Message, CreatedAt).
- [x] UI: optional message textarea under file selection; char limit 300; counter.
- [x] POST: accept message together with upload; create message row when provided.
- [x] Event Owner view: new “Guestbook” tab under Event Details listing messages with date and session nickname/email when available.
- [x] Moderation: allow event owner to delete/restore messages.
- [x] Security: rate-limit messages per session; sanitize/escape content.

## Acceptance
- [x] Guests can leave a short message; event owner can view/manage them on a dedicated tab.

==================================================

## “Join event” via QR deep link
### Goal
- Zero-typing join via event QR that opens the guest login with code prefilled.

### Build
- [x] Generate QR on Event Details that encodes `/guest/login?code={EVENT_CODE}` (no short-lived tokens).
- [x] Guest login reads `?code=` and pre-fills the field; autofocus password if required.

### Acceptance
- [x] Scanning QR on mobile opens the login with code prefilled; password is entered by the guest if required.

==================================================

## Answers to questions

Q1. Do we need a cookies popup like we see on most websites?

A1. If you only use strictly necessary cookies (session/CSRF) and no analytics/marketing, you typically don’t need a consent banner in many jurisdictions. If analytics or other non-essential cookies are planned, implement a consent banner that:
- [x] Blocks non-essential scripts until consent. (via `static/cookie-consent.js` + `type="text/plain" data-category="analytics"`)
- [x] Stores consent choice (cookie/localStorage) with a 6–12 month TTL. (180 days)
- [x] Allows easy opt-out via a “Cookie settings” link in the footer. (Footer link wired)

Q2. I want to add optional extras that are separate to plans—how should we go about this?

A2. Use add-ons layered on top of base plans.
- Data model:
	- [ ] Plan (base quotas)
	- [ ] AddOn (name, price, billing cycle, features like extra storage, extra events, custom domain)
	- [ ] Subscription (UserID, PlanID, status)
	- [ ] SubscriptionAddOn (SubscriptionID, AddOnID, quantity, active period)
- Purchase flow:
	- [ ] Add “Add-ons” section in Billing; purchase/upgrade/downgrade.
	- [ ] Proration rules if mid-cycle (or next-cycle effective for simplicity).
- Enforcement:
	- [ ] Compute effective limits = plan + sum(add-ons).
	- [ ] Show add-on usage in Billing summary.
