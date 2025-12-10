# Candidate unused/redundant code and assets

Purpose: Track likely-unused code to remove safely. For each item, we will first add a targeted test (or usage check) to prove it’s not required in the current MVP flows; only then will we delete it in a focused PR.

Notes
- Do not remove anything without: (1) a passing test that proves it’s unused or superseded, and (2) a quick grep/usage scan. Prefer small PRs per group.
- Keep migrations and DB models intact unless migrations/tests demonstrate they’re dead.

## A) Legacy React gallery artifacts (frontend/gallery)
- Paths:
  - `frontend/gallery/**` (Vite config, React sources, tests, package files)
  - `.github/workflows/frontend.yml` (CI for React build)
- Rationale: Gallery is now server-rendered via `templates/gallery.html` + `static/js/pages/gallery.js`. The React app is not served or referenced.
- Validation before removal:
  - Test: server renders gallery page without referencing React assets (assert absence of `/src/main.jsx` or React mount points).
  - Grep: no imports/links to `frontend/gallery` in templates or routers.

## B) Oversized SVG asset (static/images/Logo.svg)
- Path: `static/images/Logo.svg`
- Rationale: Multiple huge embedded segments; likely a legacy oversized asset. Consider replacing with optimized SVG/PNG in `static/images/`.
- Validation before change:
  - Test: favicon and site header still render when using a smaller logo (assert 200 on `/static/images/Logo.svg` or switch to `/static/images/logo-optimized.svg`).
  - If replacing, include the new file and update `templates/base.html` reference.

## C) Backup/temporary scripts and files under scripts/
- Paths:
  - `scripts/_create_albums_tmp.py` (temp script) — moved to `scripts/dev/`
  - `scripts/_inspect_sqlite_tables.py` (ad-hoc) — moved to `scripts/dev/`
  - `scripts/check_eventcustom_columns.py.bak` (backup) — moved to `scripts/dev/`
- Rationale: Dev-only utilities; not part of runtime. Keep if helpful, but consider pruning or moving to `scripts/dev/`.
- Validation before move/remove:
  - No runtime imports of these scripts. Grep to confirm.
  - Ensure CI and tasks don’t reference them.

Status: Completed on 2025-10-01 — scripts relocated to `scripts/dev/`.

## D) Alembic backup folder
- Path: `alembic/versions.backup/` (removed; was empty)
- Rationale: Legacy backup directory. An empty folder can be removed to reduce clutter.
- Validation:
  - None needed; ensure no scripts assume it exists.

Status: Completed on 2025-10-01 — `alembic/versions.backup/` removed.

## E) React CI workflow
- Path: `.github/workflows/frontend.yml`
- Rationale: References a React/Vite build that we no longer ship.
- Validation:
  - Confirm CI passes without this workflow (locally we just lint/test python). After deletion, ensure GH Actions still run the main CI.

## F) Albums feature: early, narrow usage
- Files:
  - `app/models/album.py`
  - Event album endpoints in `app/api/events.py` (create/list/add/remove)
  - Client wiring in `static/js/pages/gallery.js` (openAddToAlbumModal)
- Rationale: Album support is present but minimally integrated. We will NOT remove this now; flagging to review after MVP.
- Validation:
  - Keep tests to confirm album endpoints work if exposed. If we decide to de-scope for MVP, add deprecation notices instead of deletion.

## G) Debug endpoints (to gate, not delete)
- Files:
  - `app/api/gallery.py`: `/gallery/actions/delete-debug`, `/debug/gallery/delete_logs`
- Rationale: Useful in dev; must be gated off in production rather than removed.
- Validation:
  - Add tests for gating behavior based on a settings flag (e.g., `DEBUG_ROUTES_ENABLED`).

## H) Legacy frontend folder marker
- Path: `frontend/gallery/` package metadata (package.json, package-lock.json, jest config, .babelrc, index.html, src/*)
- Rationale: Fully superseded by server-rendered gallery; duplicate of A but explicitly listing files that can be pruned.
- Validation:
  - Tests as in A; ensure no template or route references build outputs.

---

## Proposed test plan before any removal

1) Add `tests/test_gallery_no_react_refs.py`
- Verify `GET /gallery` renders without referencing `frontend/gallery` assets or React script tags.
- Verify main navigation/pages don’t include React bundle references.

2) Add `tests/test_debug_routes_gated.py`
- Introduce `settings.DEBUG_ROUTES_ENABLED` (default True in dev, False in prod-like tests) and assert:
  - When disabled, `/debug/gallery/delete_logs` returns 404/403.
  - Admin mini-dashboard hides the “Raw logs (JSON)” link when disabled.

3) Optional: `tests/test_logo_asset_served.py`
- Assert `/static/images/Logo.svg` 200. If we swap to an optimized asset, update the test to the new path.

4) CI workflow sanity (documentation-only)
- After removal of `.github/workflows/frontend.yml`, ensure the main CI (`ci.yml`) still runs and is green.

---

## Removal PRs (sequenced)

- PR 1: Gate debug routes (no deletions). Add tests.
- PR 2: Remove `frontend/gallery/**` and `.github/workflows/frontend.yml`. Add tests from (1) to guard against regressions.
- PR 3: Tidy `scripts/` (move temp/backup to `scripts/dev/` or delete) — docs-only; no runtime impact.
- PR 4: Optional: Optimize or replace `Logo.svg` and update references/tests.
- PR N: Albums review post-MVP; leave intact for now.

---

If you want deeper static analysis (import graph, dead code detection), we can add a short script using `modulegraph`/`grimp` or `vulture` to cross-check unused Python functions and report findings here before touching code.
