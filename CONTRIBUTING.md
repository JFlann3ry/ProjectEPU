# Contributing

Thank you for contributing! This document explains how to set up a local dev environment, run tests, and submit PRs.

## Local setup
1. Create a virtualenv (Python 3.11+ recommended):

```powershell
py -3 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt  # optional
```

2. Copy `.env.example` to `.env` and update values.

## Running the app
```powershell
venv\Scripts\python.exe -m uvicorn main:app --reload --port 4200
```

## Tests
- Run the test suite:

```powershell
venv\Scripts\python.exe -m pytest -q
```

- For local fast runs you can run a single test file.

## Code style
- Format with Black and lint with Ruff before committing:

```powershell
venv\Scripts\python.exe -m black .
venv\Scripts\python.exe -m ruff check .
```

- We use pre-commit hooks in dev; run `pre-commit install` after installing dev requirements.

## Pull requests
- Target the `dev` branch for feature work.
- Keep PRs small and reference related issues.
- Include tests for new behavior where possible.
