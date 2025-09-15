# Privacy & Data Retention

This document describes what user data is collected, how it's stored, export and deletion policies, and retention windows.

## Data collected
- User profile: name, email, created/updated timestamps
- Events: name, code, date, customization
- File metadata: file names, types, sizes, timestamps, GPSLat/GPSLong (if present)
- Purchases and payment log metadata
- Guest messages and favorites

## Exports
- Users can request an export (manifest.json in ZIP) containing structured account data (no raw media files).
- Exports are stored under `storage/exports/{UserID}` and links expire after 7 days.

## Deletion & Retention
- Soft delete: files/records are soft-deleted and kept for X days before purge (configure retention_days).
- Export ZIPs are deleted after 7 days automatically.
- Account deletion: a grace period of Y days is applied (configurable); after that, all personal data and media are purged.

## Contact & Data Requests
- For data export or deletion requests, contact: SUPPORT_EMAIL_TO (see .env)

## Notes
- This is a skeleton; finalize retention durations and legal text with counsel.
