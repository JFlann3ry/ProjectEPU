# Email Program: User-Facing Messages

Purpose: a concise, implementation-ready catalog of the emails we send to users—from signup through reminders and billing—so engineering, design, and support share one source of truth.

Notes
- Categorization: Transactional (must send) vs. Marketing (respect user prefs).
- Preferences: honor user email prefs (marketing/product/promotions) where applicable.
- Rate limits: avoid spamming; see Throttle below each item.
- Links: always include a support link and a secure manage-preferences link.
- Variables: list the template variables required by each email.

## Onboarding & Account (Transactional)

1) Welcome + Verify Email
- Key: auth.welcome_verify
- Trigger: user signs up, email not verified
- Recipient: user
- Subject: "Verify your email to activate your account"
- Vars: user_first_name, verify_url, support_url
- Throttle: once per signup; resend on request only

2) Email Verified Confirmation
- Key: auth.verified
- Trigger: user verifies email
- Recipient: user
- Subject: "Your email is verified—welcome to EPU"
- Vars: user_first_name, dashboard_url, support_url
- Throttle: once per verification

3) Password Reset (Code/Link)
- Key: auth.password_reset
- Trigger: user requests reset
- Recipient: user
- Subject: "Reset your password"
- Vars: user_first_name, reset_url, expires_at
- Throttle: 1 per 5 min per user; show last sent time

4) Password Changed Confirmation
- Key: auth.password_changed
- Trigger: password updated
- Recipient: user
- Subject: "Your password was changed"
- Vars: user_first_name, change_time, support_url
- Throttle: transactional

5) New Login Alert (Optional, Security)
- Key: security.new_login
- Trigger: new device/IP login
- Recipient: user
- Subject: "New login to your account"
- Vars: user_first_name, ip, ua, location_guess, login_time, support_url
- Throttle: max 1 per 12h per device

6) Account Deletion Confirm (Two-step)
- Key: account.delete_confirm
- Trigger: user initiates deletion
- Recipient: user
- Subject: "Confirm account deletion"
- Vars: user_first_name, confirm_url, window_hours
- Throttle: transactional

7) Account Deleted (Final)
- Key: account.deleted
- Trigger: deletion completed
- Recipient: user
- Subject: "Your account has been deleted"
- Vars: user_first_name, effective_time, data_retention_note, support_url
- Throttle: transactional

## Plans, Billing, and Payments (Transactional)

8) Plan Purchase Receipt / Invoice Issued
- Key: billing.invoice_issued
- Trigger: plan purchase or recurring invoice created
- Recipient: user (billing contact)
- Subject: "Your EPU receipt"
- Vars: user_first_name, invoice_id, amount, currency, items[], download_url
- Throttle: transactional

9) Payment Succeeded (Invoice Paid)
- Key: billing.payment_succeeded
- Trigger: Stripe invoice paid
- Recipient: user
- Subject: "Payment received—thank you"
- Vars: user_first_name, invoice_id, amount, currency
- Throttle: transactional

10) Payment Failed (Dunning)
- Key: billing.payment_failed
- Trigger: payment attempt fails
- Recipient: user
- Subject: "We couldn’t process your payment"
- Vars: user_first_name, amount, currency, last4, retry_date, update_billing_url
- Throttle: 1 per attempt (Stripe cadence); max 1/day

11) Card Expiring Soon
- Key: billing.card_expiring
- Trigger: Stripe card expiring within 30 days
- Recipient: user
- Subject: "Your card is expiring—update billing"
- Vars: user_first_name, last4, exp_month, exp_year, update_billing_url
- Throttle: 30/15/7-day cadence

12) Subscription Changed (Upgrade/Downgrade)
- Key: billing.sub_changed
- Trigger: plan change
- Recipient: user
- Subject: "Your subscription has changed"
- Vars: user_first_name, old_plan, new_plan, proration_note, next_invoice_date
- Throttle: transactional

13) Refund Issued (If applicable)
- Key: billing.refund
- Trigger: refund processed
- Recipient: user
- Subject: "Your refund is on the way"
- Vars: user_first_name, amount, currency, invoice_id
- Throttle: transactional

14) Add-on Purchase Receipt
- Key: billing.addon_receipt
- Trigger: add-on purchase successful
- Recipient: user
- Subject: "Add-on purchased: {{ addon_name }}"
- Vars: user_first_name, addon_name, qty, amount, currency, event_name, invoice_id
- Throttle: transactional

## Data & Exports (Transactional)

15) Data Export Requested
- Key: data.export_requested
- Trigger: user starts export
- Recipient: user
- Subject: "Your export is being prepared"
- Vars: user_first_name, request_time, support_url
- Throttle: transactional

16) Data Export Ready
- Key: data.export_ready
- Trigger: export completed
- Recipient: user
- Subject: "Your export is ready—download now"
- Vars: user_first_name, download_url, expires_at
- Throttle: transactional

17) Data Export Failed
- Key: data.export_failed
- Trigger: export error
- Recipient: user
- Subject: "We couldn’t complete your export"
- Vars: user_first_name, request_id, support_url, retry_hint
- Throttle: transactional

## Event Lifecycle (Product, Mostly Transactional)

18) Event Created
- Key: event.created
- Trigger: new event created
- Recipient: user
- Subject: "Event created: {{ event_name }}"
- Vars: user_first_name, event_name, event_code, edit_url
- Throttle: transactional

19) Event Date Locked (Published)
- Key: event.locked
- Trigger: date locked/published
- Recipient: user
- Subject: "Event date locked"
- Vars: user_first_name, event_name, event_date, share_url
- Throttle: transactional

20) Event Share Links (Quick Start)
- Key: event.share_info
- Trigger: after publish or on demand
- Recipient: user
- Subject: "Share your event—links inside"
- Vars: user_first_name, share_url, guest_upload_url, qr_assets_url
- Throttle: on demand / once after publish

21) Guest Upload Digest (Daily/Weekly)
- Key: event.guest_digest
- Trigger: schedule if new uploads
- Recipient: user
- Subject: "New uploads to {{ event_name }}"
- Vars: user_first_name, event_name, period, upload_count, top_photos[], manage_url
- Throttle: daily or weekly (user choice)

## Reminders (Respect user prefs for marketing/product where appropriate)

22) Pre-Event Reminder (T-7 Days)
- Key: event.reminder_t7
- Trigger: 7 days before event date
- Recipient: user
- Subject: "One week to {{ event_name }}—final checks"
- Vars: user_first_name, event_name, event_date, checklist_url
- Throttle: once at T-7 (if date set and not passed)

23) Pre-Event Reminder (T-1 Day)
- Key: event.reminder_t1
- Trigger: 1 day before event
- Recipient: user
- Subject: "Tomorrow is {{ event_name }}—ready to go?"
- Vars: user_first_name, event_name, event_date, share_url, qr_assets_url
- Throttle: once at T-1

24) Day-of Reminder
- Key: event.reminder_day_of
- Trigger: morning of event date
- Recipient: user
- Subject: "Today’s the day—{{ event_name }}"
- Vars: user_first_name, event_name, event_date, live_gallery_url
- Throttle: once on day-of

25) Post-Event Wrap-up (T+1 Day)
- Key: event.post_wrap
- Trigger: day after event
- Recipient: user
- Subject: "How did {{ event_name }} go?"
- Vars: user_first_name, event_name, highlights_url, export_url, feedback_url
- Throttle: once at T+1

## Storage & Quota (Warnings)

26) Storage 80% Warning
- Key: storage.warn_80
- Trigger: usage >= 80%
- Recipient: user
- Subject: "You’re nearing your storage limit"
- Vars: user_first_name, used_mb, limit_mb, upgrade_url, cleanup_tips_url
- Throttle: once per +5% increase

27) Storage Full (Uploads Affected)
- Key: storage.full
- Trigger: usage >= 100%
- Recipient: user
- Subject: "Storage full—action required"
- Vars: user_first_name, used_mb, limit_mb, upgrade_url, support_url
- Throttle: 1 per day while full

## Security & Abuse (Warnings)

28) Multiple Failed Logins
- Key: security.failed_logins
- Trigger: N failed attempts within window
- Recipient: user
- Subject: "We noticed failed sign-in attempts"
- Vars: user_first_name, attempts, window, reset_url, support_url
- Throttle: 1 per 6h

29) Suspicious Activity Detected
- Key: security.suspicious
- Trigger: unusual pattern (geo/device)
- Recipient: user
- Subject: "Unusual activity on your account"
- Vars: user_first_name, details (ip, ua), timestamp, reset_url, support_url
- Throttle: 1 per 12h

## Support (Transactional)

30) Support Ticket Received (Contact Form)
- Key: support.ticket_received
- Trigger: contact form submitted
- Recipient: user
- Subject: "We received your message"
- Vars: user_first_name, ticket_id, request_id (if error), sla_hint, support_url
- Throttle: transactional

31) Support Ticket Updated
- Key: support.ticket_update
- Trigger: agent reply or status change
- Recipient: user
- Subject: "Update on your support ticket"
- Vars: user_first_name, ticket_id, reply_preview, portal_url
- Throttle: transactional

## Marketing & Education (Respect marketing prefs)

32) Getting Started Tips (D+3)
- Key: edu.getting_started
- Trigger: 3 days after signup (no event yet)
- Recipient: user
- Subject: "3 tips to get value fast"
- Vars: user_first_name, tutorial_url, examples_url, pricing_url
- Throttle: once; skip if event created

33) Feature Highlight (Live Gallery)
- Key: edu.feature_live_gallery
- Trigger: user without live gallery usage
- Recipient: user
- Subject: "Make your event live"
- Vars: user_first_name, feature_url, extras_url (formerly addons_url)
- Throttle: max 1 per 30 days

34) Trial Ending (If trials enabled)
- Key: marketing.trial_ending
- Trigger: trial ends in 3 days
- Recipient: user
- Subject: "Your trial is ending—keep your access"
- Vars: user_first_name, end_date, upgrade_url
- Throttle: 3/1 day cadence

---

## Implementation Hints
- Template IDs: use the Key values above for lookup in code and template files.
- Deliverability: add List-Unsubscribe for marketing; DMARC/SPF/DKIM configured.
- Preference Center: link at footer for marketing/product emails; transactional always sent.
- Scheduling: a simple scheduler or background worker (e.g., APScheduler, RQ/Celery) for reminders/digests.
- Error context: include `request_id` in failure-related emails (we log it server-side already).
