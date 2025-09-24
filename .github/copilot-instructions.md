## ProjectEPU — Copilot instructions for coding agents

Assistant checklist (short):

- If the user prefixes with `Use PERMANENT_INSTRUCTIONS`: re-read `PERMANENT_INSTRUCTIONS.md`, summarize rules in one paragraph, ask one clarifying question only if material, then proceed.
- Before committing schema changes: create one Alembic revision (`alembic revision --autogenerate -m "..."`), inspect/edit migration, commit, then `alembic upgrade head` locally.
- Always run lint and tests after code changes and report the results (use `scripts/lint_and_test.py` on Windows).
- When adding behavior, add focused tests (happy path + at least one edge/failure); mark long integration tests with `@pytest.mark.integration`.
- Preserve request logging, `X-Request-ID` headers, and DB error logging when editing handlers in `main.py`.

Be brief and practical. Prioritize changes that keep the app runnable locally and avoid changing DB schemas without an accompanying Alembic migration.

- Big picture: FastAPI monolith with Jinja2 server-rendered pages plus a small JS layer. Key entrypoints: `main.py` (app wiring), `app/main.py` (test-friendly re-export), `run.py` (dev runner). DB access via `db.get_db()` and SQLAlchemy models in `app/models/`. Templates live in `templates/`, static assets under `static/`, media in `storage/`.

- Local dev workflow:
  - Create a venv and install: `py -3 -m venv venv; venv\Scripts\activate; pip install -r requirements.txt`
  - Run dev server: `uvicorn main:app --host 0.0.0.0 --port 4200 --reload` or `python run.py`.
  - Migrations: use Alembic (root `alembic.ini` + `alembic/`): `alembic upgrade head`.
  - Lint & tests: `python -m ruff check .` and `python -m pytest -q`; helper script: `scripts/lint_and_test.py`.

- Database/Testing notes:
  - Production uses SQL Server via settings in `app/core/settings.py`; tests can use in-memory SQLite if `TEST_SQLITE=1` is set (see `db.py`).
  - Always prefer `db.get_db()` dependency injection in routers; avoid creating engine/session directly.

- Logging & errors:
  - Request middleware adds `X-Request-ID` header and writes structured logs (see `main.py`). When adding handlers, preserve the request-id header.
  - Errors (404/HTTPException/500) are logged to DB via `AppErrorLog` where possible — avoid losing stack traces.

- Conventions & patterns to follow:
  - Routes are modular under `app/api/*`. Register routers in `main.py` in the existing order (static mounts and events_create before `events` to prevent route conflicts).
  - Use `templates.TemplateResponse(request, "...")` for HTML responses and include `request` in context.
  - Theme and UI: theme variables live in templates and are shared via `_theme_vars.html` + `static/theme.css`.
  - File uploads: save under `storage/{userId}/{eventId}/` and record metadata in `app/models`.

- Integration points:
  - Email: `app/services/email_utils.py` (aiosmtplib). In dev the send may no-op if credentials missing.
  - Stripe webhooks: billing code under `app/api/billing` — follow existing webhook handling patterns.
  - Optional Redis for rate-limiting controlled by `REDIS_URL` in `.env` and settings in `app/core/settings.py`.

- What to avoid changing without coordination:
  - DB connection string construction in `db.py` (handles ports and instance names).
  - Request logging and exception handlers in `main.py` — they ensure AppErrorLog writes and headers.
  - Route ordering in `main.py` (static routes before parameterized routes).

- Quick examples to reference in edits:
  - Use DB: from `db import get_db` then `def endpoint(db=Depends(get_db)):`
  - Return file response: `return FileResponse("static/favicon.png")` (see `/favicon.ico`).

- Developer commands to surface when editing or creating PRs:
  - Setup: `py -3 -m venv venv; venv\Scripts\activate; pip install -r requirements.txt`
  - Run dev: `python run.py` or `uvicorn main:app --reload`
  - Lint & tests: `python scripts/lint_and_test.py`
  - Alembic migrations: `alembic revision --autogenerate -m "msg"` then `alembic upgrade head`

If anything here is unclear or you need more examples (tests, models, or a specific router), tell me which area and I will expand the instructions with short examples from the codebase.

---

Assistant protocol & required project procedures (merge from PERMANENT_INSTRUCTIONS)

- When a human prefixes a request with `Use PERMANENT_INSTRUCTIONS`, follow this flow:
  1. Re-read `PERMANENT_INSTRUCTIONS.md` and summarize the specific rules you'll apply in one paragraph.
  2. Ask a single clarifying question only if a choice materially affects implementation (for example: enabling strict CSP vs allowing known CDNs).
  3. Proceed with edits and run lint/tests as described below. If you make changes, list edited files and the lint/test results.

- Alembic / schema changes (mandatory steps):
  1. Create a single Alembic revision per logical change: `alembic revision --autogenerate -m "describe change"`.
  2. Inspect and edit the generated migration for idempotency and safe downgrades.
  3. Commit the migration file and push the branch. Keep migrations small and focused.
  4. Run `alembic upgrade head` locally to verify the migration applies cleanly.
  5. If multiple migrations are required, apply and test them one-by-one in order.
  6. Prefer backward-compatible code that works with both pre- and post-migration schemas; run migrations in production as a separate step.

- Lint, tests, and new-tests policy (required):
  - Always run lint and tests after code changes and report results.
  - When modifying behavior add tests in `tests/` (happy path + at least one edge/failure case).
  - Keep tests focused and fast. Mark truly long integration tests with a pytest marker (e.g., `@pytest.mark.integration`) and document them in the PR.
  - Reuse repository fixtures where possible; add to `tests/conftest.py` only when needed.

If you'd like I can further compress these into a one-paragraph assistant checklist at the top of this file or expand with short examples for common actions (creating a migration, adding a test, running the lint/test script).
