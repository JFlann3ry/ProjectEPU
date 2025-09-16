Permanent Instructions for the Assistant

Purpose
 This file defines persistent, human-readable instructions the assistant should follow when working in this repository. Treat it as the single source of truth for recurring preferences and project-specific conventions.


Assistant confirmation behavior
 When you prefix a user request with "Use PERMANENT_INSTRUCTIONS", the assistant will:
	1. Read `PERMANENT_INSTRUCTIONS.md` from the repository root.
	2. Reply with a one-paragraph summary of the specific rules it will apply to the requested task and any assumptions it made.
	3. Ask one clarifying question only if a choice materially affects the implementation (for example: "enable CSP strict mode or allow known CDNs?").
	4. Proceed to make edits and run checks (lint/tests) per the document. If changes are made, the assistant will list the edited files and the test/lint results.

Rules 

 Always run lint and tests after making code changes, and report results.
 Use the project's existing style and formatting tools (black/ruff) when modifying Python files.
 When editing templates, keep changes minimal and maintain existing class names.
 For UI changes, run a quick visual sanity check and adjust spacing if needed.



Alembic and schema change steps (one-at-a-time)
 When a change requires DB schema migration, follow these steps exactly to avoid migration conflicts and ensure reviewability:
	1. Create a single Alembic revision for each logical schema change using `alembic revision --autogenerate -m "describe change"`.
	2. Inspect the generated migration and edit it to ensure idempotency and safe downgrades.
	3. Commit the migration file and push the branch. Keep migrations small and focused (one model/table change per revision when practical).
	4. Run `alembic upgrade head` locally to verify the migration applies cleanly.
	5. If multiple migrations are required, apply and test them one-by-one in order; do not batch multiple unrelated schema changes in a single revision.
	6. For release: deploy code that can work with both pre- and post-migration schema if possible (backwards-compatible), then run migrations in production as a separate step.

Lint, tests, and new tests policy
 Every code change that modifies behavior or adds a feature must include tests. Follow this pattern:
	1. Add or update unit/integration tests for the changed behavior in `tests/` (happy path + at least one failure/edge case).
	2. Run lint and tests locally (`ruff check .` then `pytest -q`). Fix lint errors before committing.
	3. Keep test scope focused and fast. If a new long-running integration test is required, mark it with a pytest marker (e.g., `@pytest.mark.integration`) and add a short note in the PR description.
	4. When adding tests rely on fixtures already in the repo where possible; add new fixtures in `tests/conftest.py` if needed.
	5. Document any non-obvious test setup steps in the PR description.


Prompt template (copy/paste)
Use PERMANENT_INSTRUCTIONS: <what to do>

