# Missing Docs and Action Plan

This file lists documentation currently missing or incomplete in the repository and provides skeletons/next steps so contributors can fill them in. Create issues or PRs against `dev` and link back to this file when items are started/complete.

## Summary of missing or incomplete docs

- .env example / runtime config: essential for onboarding developers and deployments (`.env.example`)
- Privacy & Data Retention / GDPR: document retention policies, deletion flow, export details (`PRIVACY.md`)
- CONTRIBUTING: development conventions, tests, PR template explanation (`CONTRIBUTING.md`)
- MIGRATIONS_GUIDE: how to generate and apply Alembic revisions safely (SQL Server notes) (`MIGRATIONS.md`)
- TESTING_GUIDE: how to run tests locally and expected test DB setup (`TESTING.md`)
- DEPLOYMENT: Docker, systemd+Nginx examples, backups, env var management (`DEPLOYMENT.md`)
- SECURITY_GUIDE: recommended secrets management, cookie settings, CSP guidance (`SECURITY.md`)
- CHANGELOG: release notes / changelog skeleton (`CHANGELOG.md`)

---

## Suggested files with skeletons

### `.env.example`

Purpose: provide minimal environment variables required to run the app locally and in CI.

Content skeleton:

```
DB_SERVER=localhost
DB_NAME=EPU
DB_USER=sa
DB_PASSWORD=changeme
DB_DRIVER=ODBC Driver 17 for SQL Server

SECRET_KEY=replace-with-random
BASE_URL=http://localhost:4200

GMAIL_USER=
GMAIL_PASS=

STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

LOG_LEVEL=INFO
LOG_JSON=false

# Optional: redis for rate limiting
REDIS_URL=
```

Acceptance: `.env.example` present and referenced in README with guidance on secrets.

---

### `PRIVACY.md`

Purpose: document export, deletion, retention windows, and any PII considerations.

Sections to include:
- Data types collected
- Export behavior (what's included/excluded)
- Deletion/retention policy and purge schedule
- Contact/legal email to request data or deletion
- Notes on backups and how long backups are kept

---

### `CONTRIBUTING.md`

Purpose: help external contributors set up dev environment, run tests, and follow project conventions.

Sections:
- Local environment setup (python version, venv, install requirements)
- How to run the app locally (run commands, .env.example usage)
- Tests (run pytest, run individual tests, TestClient notes)
- Code style (black/ruff pre-commit + how to run them locally)
- Branching and PR process (branch names, rebase vs merge, PR template)

---

### `MIGRATIONS.md`

Purpose: explain Alembic usage, patterns for generating migration SQL for SSMS, and merging heads.

Sections:
- How to create an autogenerate revision
- When to hand-edit migration SQL for SQL Server
- How to generate raw SQL for manual application in SSMS
- Merge migrations: when and how to create a merge head
- Troubleshooting: common errors (duplicate columns, multiple heads, blocked sessions)

---

### `TESTING.md`

Purpose: document test setup, `TEST_SQLITE` usage, `db_session` fixture behavior, and CI notes.

Sections:
- Running unit tests locally (python -m pytest -q)
- Using TEST_SQLITE=1 for in-memory SQLite runs (warnings about schema)
- Setting up test DB (if using local SQL Server) and credentials
- Notes on flaky tests and how to debug (DB transactions, isolation level, _safe_commit helper)

---

### `DEPLOYMENT.md`

Purpose: capture recommended deployment approaches (Docker, systemd + Nginx), healthchecks, and backups.

Sections:
- Docker: build/run example, healthcheck, non-root user
- Systemd: example `deploy/epu.service` usage and env file
- Nginx: recommended config and security headers
- Backups: DB + storage backup suggestions and restore steps

---

### `SECURITY.md`

Purpose: centralize security-related guidance: cookie settings, CSP suggestions, encryption/secret rotation.

Sections:
- Cookie flags and session lifetime
- CSP and removing inline JS plan
- Secrets management (env, vaults)
- Recommended Sentry/OTel settings
- Upload handling: MIME sniffing, size limits, filename sanitization

---

### `CHANGELOG.md`

Purpose: track release notes and important changes. Use keep-a-changelog style.

Skeleton:

```
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- notes...

## [0.1.0] - YYYY-MM-DD
- initial release notes
```

---

## Action items

- [ ] Add `.env.example` from skeleton and link from `README.md`
- [ ] Add `PRIVACY.md` with retention and export details
- [ ] Add `CONTRIBUTING.md` describing dev setup and pre-commit
- [ ] Add `MIGRATIONS.md` describing safe Alembic patterns for SQL Server
- [ ] Add `TESTING.md` describing test DB setup and `TEST_SQLITE` mode
- [ ] Add `DEPLOYMENT.md` showing Docker and systemd examples
- [ ] Add `SECURITY.md` with cookie/CSP/secret guidance
- [ ] Add `CHANGELOG.md` and start tracking releases

If you'd like, I can create these files now with the skeleton content above and open a PR; tell me which files to create first or say "create all" and I'll add them all in one patch and run quick lint checks (no spellcheck) afterwards.
