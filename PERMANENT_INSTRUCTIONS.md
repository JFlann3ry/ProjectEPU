Permanent Instructions for the Assistant

Version: 2025-10-02  •  Owners: ProjectEPU maintainers  •  Canonical file: PERMANENT_INSTRUCTIONS.md

Purpose
This file is the single source of truth for how the assistant should work in this repo. It encodes expectations, safety rails, and workflow conventions.

TL;DR — Assistant checklist
- Before edits: plan todos, then gather minimal context needed; make at most 1–2 assumptions if details are missing.
- Prefer VS Code Tasks for install/run/lint/test over ad‑hoc commands (Windows-friendly).
- After changes: run Ruff and Pytest, and report results. Keep the repo green.
- Keep diffs small; preserve style, public APIs, logging, and route order.
- Use db.get_db() for DB access; avoid creating engines/sessions directly.
- Always include CSRF where required (cookie + hidden input + verification on POSTs).
- Schema changes require an Alembic revision and local upgrade verification (steps below).

Assistant confirmation behavior
When a user prefixes a request with "Use PERMANENT_INSTRUCTIONS":
1) Re-read this file and reply with a one-paragraph summary of the rules you’ll apply (plus assumptions if any).
2) Ask exactly one clarifying question only if a choice materially affects implementation.
3) Proceed with edits and run lint/tests. If changes were made, list edited files and the lint/test results.

Quick commands (prefer Tasks)
- Install runtime deps: use the VS Code task “install:runtime”.
- Install dev deps: task “install:dev”.
- Run dev server: task “run:dev”.
- Lint: task “lint”.
- Tests (fast path): task “test” or “lint+test (windows-safe)”.
- DB migrate to head: task “db:migrate”.
(These tasks are already defined in the workspace; they work with Windows PowerShell.)

Quality gates (Done means all pass)
1) Lint: ruff check . (no errors)
2) Tests: pytest -q (non-flaky tests passing)
3) Migrations: if schema changed, `alembic upgrade head` was applied locally
4) No broken imports, obvious runtime errors, or unpinned breaking changes

Change policies
- Minimal diffs: touch only what’s necessary; avoid unrelated reformatting.
- Preserve logging and request headers: keep X-Request-ID propagation and DB error logging.
- Route order: don’t move router registration unless explicitly requested (static mounts and events_create before parameterized routes).
- Security:
  - CSRF: issue token (cookie + hidden input + meta) and validate on state-changing POSTs; allow TestClient UA bypass in tests.
  - SQL: use ORM or sqlalchemy.text() with bound parameters; no string concatenation.
  - Rate limiting: use provided settings; prefer Redis if configured; otherwise in-memory is acceptable.
- DB access: prefer `db.get_db()` dependency injection in routers; do not construct engines/sessions inline.

Alembic and schema change steps (one-at-a-time)
1) `alembic revision --autogenerate -m "describe change"`
2) Inspect/edit migration for idempotency and safe downgrade
3) Commit the migration; keep the revision focused
4) Run `alembic upgrade head` locally
5) If multiple are needed, apply and test one-by-one
6) Prefer backward-compatible code that works pre/post migration

Conventions and patterns
- Templates: always pass `request` in context; keep class names stable; use ARIA roles for accessibility (gallery container role=list; tiles role=listitem; status regions have role=status and aria-live=polite).
- Client JS: include CSRF token from `meta[name="csrf-token"]` or a hidden input for POSTs; avoid brittle selectors; add tiny focus traps for modals.
- Files/storage: keep media under `storage/{userId}/{eventId}/`; don’t change paths without updating dependent services.
- Admin and debug: admin routes require admin; debug routes behind explicit settings flags.

Testing policy
1) For behavior changes, add tests (happy path + one failure/edge case).
2) Keep tests fast; mark true end-to-end or long ones with `@pytest.mark.integration`.
3) Respect line length to avoid Ruff E501; split long assertions or strings.
4) Prefer existing fixtures; extend `tests/conftest.py` only when needed.
5) If a change can’t be fully tested quickly, add a focused smoke test and note follow-ups.

Do / Don’t
- Do: use db.get_db(), validate CSRF, preserve X-Request-ID, add migrations for schema changes, run tasks for lint/tests.
- Don’t: reorder routers casually, remove error logging, execute raw SQL without params, or introduce React/SPA frameworks.

Examples (snippets)
- Server POST with CSRF validation (FastAPI):
  - In endpoint signature: `request: Request, csrf_token: str | None = Form(None)`
  - Validate: compare cookie CSRF to form token and call `validate_csrf_token(csrf_token, session_id)`; on failure, 303 back to referer (skip strict for TestClient UA).
- Template with CSRF:
  - Hidden input: `<input type="hidden" name="csrf_token" value="{{ csrf_token or '' }}">`
  - Meta: `<meta name="csrf-token" content="{{ csrf_token or '' }}">`
- JS POST with CSRF:
  - `const csrf = (document.querySelector('meta[name="csrf-token"]').content || ''); fd.append('csrf_token', csrf);`
- SQL stored procedure with params:
  - `db.execute(text("EXEC dbo.GetEventGalleryOrder :eid").bindparams(eid=event_id))`

Prompt template (copy/paste)
Use PERMANENT_INSTRUCTIONS: <what to do>

