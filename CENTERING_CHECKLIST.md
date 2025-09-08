# Centering Checklist

Use this list to verify that every page renders centered within the 980px container. Check off each as you confirm.

Legend:
- [ ] Not checked
- [x] Centered OK

Last updated: 2025-09-04

## Public
- [x] / — home.html
- [x] /examples — examples.html
- [x] /terms — terms.html
- [x] /terms/embed — components/terms_text.html (embed fragment; N/A container)
- [x] /privacy — privacy.html
- [x] /faq — faq.html
- [x] /about — about.html
- [x] /tutorial — tutorial.html
- [x] /pricing — pricing.html
- [x] /plans — pricing.html

## Auth
- [x] /login — log_in.html
- [x] /signup — sign_up.html
- [x] /verify-notice — verify_notice.html
- [x] /verify — verify_notice.html (alias)
- [x] /verify-email — log_in.html (verification result page)
- [x] /logout — redirect to /login (no layout)

## Account
- [x] /account/delete — account_delete.html

## Profile
- [x] /profile — profile.html
- [x] /profile/email-preferences — email_prefs.html
- [x] /profile/edit — edit_profile.html
- [x] /profile/password — password_change.html
- [x] /profile/password/confirm — password_change_done.html

## Events (owner)
- [x] /events — events_dashboard.html
- [x] /events/create — create_event.html
- [x] /events/{event_id} — event_details.html
- [x] /events/{event_id}/edit — edit_event.html

## Public Share
- [x] /e/{code} — share_event.html

## Gallery
- [x] /gallery — gallery.html

## Guest Flow
- [x] /guest/login — guest_log_in.html
- [x] /guest/upload/{event_code} — guest_upload.html

## Billing & Add-ons
- [x] /billing/summary — billing_summary.html
- [x] /billing/purchase/{purchase_id} — billing_purchase.html
- [x] /addons — addons.html

(Admin-only)
- [x] /admin/billing/manage — admin_billing.html

## Admin (internal)
- [x] /admin — admin_dashboard.html
- [x] /admin/users — admin_users.html
- [x] /admin/errors — admin_errors.html
- [x] /admin/event/{event_id} — admin_event.html
- [x] /admin/components — admin_components.html
- [x] /admin/themes — admin_themes.html (intentionally wide editor layout)
- [x] /admin/themes/audit — admin_themes_audit.html

## Support
- [x] /contact — contact.html
- [x] /contact/sent — contact_sent.html

## Error Pages
- [x] 404 — 404.html (e.g., visit a non-existent route or unauthorized event gallery)
- [x] 500 — 500.html (simulate only; not routed directly)

Notes:
- Redirect-only and non-HTML endpoints are omitted (e.g., /qr, /health, /robots.txt).
- Paths with parameters ({event_id}, {purchase_id}, {code}) can be tested with any valid value.
- The /terms/embed endpoint serves a bare fragment for embedding in modals/iframes and intentionally has no container.
- Admin Themes (/admin/themes) uses a full-width editor layout by design and isn’t constrained to the 980px container.