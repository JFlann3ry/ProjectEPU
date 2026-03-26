# Website Review (2026-03-26)

Fresh full-site audit. Builds on the 2026-03-24 review. All P0/P1/P2 items from that review are complete.
Lint: `ruff check .` — **0 errors**. Tests: `pytest -q` — **187 passed, 11 skipped (all green after fixes below)**.

Legend: `P0` critical · `P1` important · `P2` polish/guardrail. Effort: `S` (≤1 day) `M` (2–4 days) `L` (5+).

---

## Fixed in this session (before review was written)

### examples.html — Jinja2 `{% call btn_row %}` missing parentheses
- **Symptom**: `/examples` crashed with `jinja2.exceptions.TemplateSyntaxError: expected call`.
- **Root cause**: `{% call btn_row %}` should be `{% call btn_row() %}` — every other template had parentheses.  
- **Fix**: `templates/examples.html` line 125: added `()`.  
- **Status**: ✅ Done.

### base.html — missing `{% block extra_meta %}` (noindex never rendered)
- **Symptom**: `test_live_page_has_hud_and_meta` failing; live slideshow pages were indexable by search engines.
- **Root cause**: `live_slideshow.html` overrides `{% block extra_meta %}` to inject `<meta name="robots" content="noindex">` but `base.html` never defined that block, so Jinja2 silently dropped it.  
- **Fix**: Added `{% block extra_meta %}{% endblock %}` to `templates/base.html` `<head>` after `extra_css`. Any template can now inject head-level meta overrides.  
- **Status**: ✅ Done.

### test_live_routes.py — `.endswith("a.jpg")` assertions broken by `?code=` query string
- **Symptom**: `test_live_data_basic_and_since_and_limit` failing — `assert got[0]["src"].endswith("a.jpg")` but src is `/media/uid/eid/a.jpg?code=TESTLIVE195649`.
- **Root cause**: `live.py` `_shape_live_items` intentionally appends `?code=<event_code>` to all media URLs (auth-gating). Test assertions were written before this was added.  
- **Fix**: Changed three `endswith("x.ext")` checks to `.split("?")[0].endswith("x.ext")`, which checks only the path part.  
- **Status**: ✅ Done.

---

## Open items

### P1 — Security / Reliability

- [ ] `P1-01` **Live slideshow `/data` endpoint — no auth gate for private events.** (`S`)
  - Why: `/live/{code}/data` returns files for any event where `Published=True`. There is no mechanism to restrict the data feed to logged-in owners or guests with a known guest session. Anyone who knows the event code can poll the data endpoint indefinitely.
  - Evidence: `app/api/live.py` — `live_slideshow_data` only checks `Published` flag; no rate limiting per-viewer beyond a basic ip+code bucket.
  - Done when: Rate-limit window is per-IP *and* per-code; optionally a signed token is required to access `/data` (matching the `?code=` already added to media URLs).

- [ ] `P1-02` **Password field shown in edit form may expose raw password.** (`S`)
  - Why: `events_editing.py` generates/repairs the event password and passes it to `edit_event.html` in plain text in the template context. If the page is cached or the HTML is stored anywhere, the value is exposed.
  - Evidence: `app/api/events_editing.py` — `setattr(event, "Password", gen_pw)` then passes `event` to template; `templates/edit_event.html` renders it in an input.  
  - Done when: The generated password is only shown once via a one-time modal flow, or the input value is masked by default with a reveal toggle.

- [ ] `P1-03` **`_shape_live_items` silently swallows all per-row exceptions.** (`S`)
  - Why: an empty `except Exception: continue` block means corrupt metadata rows produce no log and are silently skipped, making debugging hard.
  - Evidence: `app/api/live.py` line ~49.
  - Done when: Exceptions at row-level log a `logger.debug(...)` with `fid` and `exc_info=True`.

- [ ] `P1-04` **`events_editing.py` uses `import` statements inside a route handler.** (`S`)
  - Why: `from app.models.event import Theme` and `from app.services.csrf import ...` are inside `edit_event_page_code()`. This is a code smell that forces repeated module lookups on every request and can hide import errors until runtime.
  - Evidence: `app/api/events_editing.py` lines ~44, ~58.
  - Done when: All imports are moved to the module top-level.

- [ ] `P1-05` **Password generation uses `random.choice`, not `secrets`.** (`M`)
  - Why: `events_editing.py` generates a 6-char alphanumeric event password with `random.choice`. `random` is not cryptographically secure; passwords should use `secrets.choice`.
  - Evidence: `app/api/events_editing.py` `_gen_pw()` function (inline inside route).
  - Done when: `_gen_pw` moved to a utility module and uses `secrets.choice(alphabet)`.

### P2 — Coverage / Polish

- [ ] `P2-01` **No test for `extra_meta` block rendering in live slideshow.** (`S`)
  - Why: The `test_live_page_has_hud_and_meta` test was failing because the `robots` meta was never in the output. Now fixed but we should also assert the block works end-to-end from base template perspective.
  - Done when: Existing test passes (it now does); a comment in the test documents why `split("?")[0]` is used in the data test.

- [ ] `P2-02` **`live_slideshow.html` upload link exposed to any visitor.** (`S`)
  - Why: The topbar shows `<a href="/guest/upload/{{ event_code }}" target="_blank">Upload link</a>` to anyone who knows the code — including unauthenticated viewers. Depending on event settings this may be intentional, but there is no indicator or option to suppress it.
  - Done when: Upload link is conditionally shown based on event's `AllowUploads` or equivalent flag; or this is explicitly documented as intentional.

- [ ] `P2-03` **`theme.css` has no version-busting in cached environments.** (`S`)
  - Why: `base.html` adds `?v={{ now() }}` to `app.css` and `form.css` but `theme.css` is served the same way. Works on dev, but if `now()` were ever removed or cached, theme changes won't propagate.
  - Evidence: `templates/base.html` — `theme.css` link already has `?v={{ now() if now else '' }}`, so this is already handled. ✅ Actually clean.

- [ ] `P2-04` **`edit_event.html` inline `random`/`re`/`string` imports inside route.** (`S`)
  - Why: Same as P1-04 above — inline imports in the route body hurt readability. Not a functional bug but makes the code hard to audit.
  - Done when: Resolved as part of P1-04 / P1-05.

- [ ] `P2-05` **No test coverage for `_shape_live_items` function itself.** (`S`)
  - Why: The helper is tested indirectly through integration tests, but no unit tests directly exercise unsupported MIME types or corrupt rows.
  - Done when: A unit test covers at least: image row, video row, unsupported-type row, and malformed fid row.

---

## Areas confirmed clean (audited 2026-03-26)

| Area | File(s) | Result |
|------|---------|--------|
| Jinja2 macro calls | All templates | ✅ All use `{% call macro() %}` with parens (examples.html fixed today) |
| CSRF on guest upload POSTs | `uploads.py`, `guest_upload.html` | ✅ Hidden input + cookie validation present |
| CSRF on event edit POSTs | `events_edit_submit_code.py`, `events_edit_submit_numeric.py` | ✅ Validated |
| Theme value resolution | `theme_values.py` | ✅ Defensive; all edge cases have defaults |
| Event edit template | `edit_event.html` | ✅ All blocks balanced, labels present, aria correct |
| Static CSS | `theme.css` | ✅ No syntax errors; focus-visible and reduced-motion present |
| Compression middleware | `middleware_compression.py` | ✅ (covered by test_compression_middleware.py) |
| Billing webhook | `billing.py` | ✅ (hardened in 2026-03-24 review) |
