Playwright E2E tests

Requirements:
- Python dependencies: playwright, pytest-playwright
- Install Playwright browsers: `playwright install` (after installing the package)
- Run the dev server (e.g., `python run.py` or `uvicorn main:app --reload --port 4200`)

Run a single test:

Set env var and run pytest:

On Windows PowerShell:

$env:E2E_PLAYWRIGHT = '1'; python -m pytest tests/e2e/test_gallery_delete_e2e.py -q

Notes:
- Tests expect the app to be reachable at http://localhost:4200
- The test creates DB rows using the project's test fixtures and sets a session cookie in the browser context.
- Running E2E tests in CI requires starting the server and having Playwright browsers installed.
