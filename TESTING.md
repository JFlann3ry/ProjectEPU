# Testing Guide

This document describes how to run the test suite and how the test fixtures behave.

## Running tests
- Run all tests:

```powershell
venv\Scripts\python.exe -m pytest -q
```

- Run an individual test file:

```powershell
venv\Scripts\python.exe -m pytest tests/test_webhook_idempotency.py::test_webhook_idempotent -q
```

## Test DB modes
- `TEST_SQLITE=1` will run tests using an in-memory SQLite DB. This mode strips schema names to avoid `dbo.` prefixes.
- The default test run uses the configured DB (SQL Server) and transactional fixtures.

## Fixtures
- `db_session` fixture provides a connection-bound transactional session rolled back at teardown.
- `_safe_commit()` in the webhook handler detects test session wiring and prefers `db.flush()` to avoid detaching instances.

## Debugging tips
- If tests fail with foreign key errors, ensure test fixtures create required rows (users, plans) or use the provided helper fixtures.
- Use `-k` to run tests matching a substring.

## CI notes
- The CI pipeline should install requirements-dev and run `ruff` and `pytest`.
