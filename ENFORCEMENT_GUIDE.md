# Enforcement Guide

This guide explains how to enforce plan-based limits (upload/download windows, feature gating) and how to test them. See also: `TESTING.md` and the plan feature helpers in `app/core/plan_features.py`.

## Table of Contents

- [Step 3: Time-Based Enforcement](#step-3-time-based-enforcement)
- [Step 4: UI/UX](#step-4-uiux)
- [Step 5: Testing](#step-5-testing)
- [Security & edge cases](#security--edge-cases)


## Step 3: Time-Based Enforcement

- For upload/download windows, check event creation date + plan duration using helper functions (see `app/core/plan_features.py`).

Example usage:

```python
from app.core.plan_features import upload_window_active, download_window_active
from fastapi import HTTPException

if not upload_window_active(user, event.created_at):
    raise HTTPException(status_code=403, detail="Upload window expired. Upgrade for more time.")

if not download_window_active(user, event.created_at):
    raise HTTPException(status_code=403, detail="Download window expired. Upgrade for more time.")
```

## Step 4: UI/UX

- In templates, use `has_feature(user, feature)` to show/hide buttons and links.

Example (Jinja2):

```jinja2
{% if has_feature(user, 'can_view_gallery') %}
  <a href="/gallery">View Gallery</a>
{% else %}
  <a href="/upgrade">Upgrade to unlock gallery</a>
{% endif %}
```

## Step 5: Testing

- Write tests for each plan to ensure only allowed features are accessible.
- Test upload/download window expiry for each plan.

### Testing hints

- Use fixtures that create plans with differing `max_storage_per_event_mb`, `upload_months`, and `download_months` values.
- Assert HTTP 403 responses for expired windows and 200 for valid windows.

---

Last updated: 2025-09-12

## Security & edge cases

- Use server-side time (database or trusted server time) for enforcement checks to avoid client clock skew.
- Prefer transactional checks when granting entitlements to avoid race conditions (use DB transactions / savepoints).
- Reject or sanitize SVG uploads (`image/svg+xml`) as they can contain active content — either disallow or sanitize before serving.
- For upload size checks, validate client-reported sizes and also enforce server-side limits; prefer streaming writes to avoid large memory usage.

## Changelog

- 2025-09-12: Cleaned document, added examples, TOC, and security hints.
