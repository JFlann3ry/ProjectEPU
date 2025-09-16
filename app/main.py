# Lightweight re-export so tests and imports that expect `app.main` work.
# Avoid importing heavy test-only logic here; simply re-export the FastAPI application
# defined at the repository root `main.py`.
from main import app as app
