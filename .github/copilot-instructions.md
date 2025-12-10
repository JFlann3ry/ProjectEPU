## ProjectEPU — Copilot instructions (mirror)

Canonical source of truth: `PERMANENT_INSTRUCTIONS.md` at repo root.

Note on drift: Do not update this file without updating the canonical document. If instructions differ, follow `PERMANENT_INSTRUCTIONS.md`.

Assistant quickstart (short)
- Re-read `PERMANENT_INSTRUCTIONS.md` before non-trivial work.
- Plan todos, then prefer VS Code Tasks for install/run/lint/test (Windows-friendly).
- Keep diffs small; preserve logging (X-Request-ID), route order, and existing style.
- Run Ruff and Pytest after changes and report results.
- Schema changes use Alembic (single focused revision, inspect, upgrade head locally).
- Security: enforce CSRF on state-changing POSTs; use bound params for SQL; use `db.get_db()`.

“Use PERMANENT_INSTRUCTIONS” flow
1) Re-read `PERMANENT_INSTRUCTIONS.md` and reply with a one-paragraph summary of rules you’ll apply (include assumptions if any).
2) Ask a single clarifying question only if it materially changes implementation.
3) Proceed with edits and run lint/tests; if changes were made, list edited files and results.

Quick commands (prefer Tasks)
- install: `install:runtime`, dev: `install:dev`
- run dev: `run:dev`
- lint: `lint`
- tests: `test` or `lint+test (windows-safe)`
- db migrate: `db:migrate`

For details on conventions (templates, accessibility, security rules, examples), see `PERMANENT_INSTRUCTIONS.md`.
