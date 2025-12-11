import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import settings

# Allow tests to opt into an in-memory SQLite DB to avoid network hangs when
# MSSQL is not available. Set environment variable TEST_SQLITE=1 when running
# pytest to enable this.
if os.getenv("TEST_SQLITE") == "1":
    # Use StaticPool so the same in-memory DB is reused across connections.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Build connection string from centralized settings
    server = settings.DB_SERVER
    database = settings.DB_NAME
    username = settings.DB_USER
    password = settings.DB_PASSWORD
    driver = settings.DB_DRIVER
    port = settings.DB_PORT

    # If DB_SERVER already contains a port (":" or ",") or an instance name ("\\"),
    # use it as-is; otherwise append :port
    if any(sep in (server or "") for sep in (":", ",", "\\")):
        hostpart = server
    else:
        hostpart = f"{server}:{port}"

    connection_string = (
        f"mssql+pyodbc://{username}:{password}@{hostpart}/{database}"
        f"?driver={driver.replace(' ', '+')}"
    )

    engine = create_engine(
        connection_string,
        connect_args={
            "TrustServerCertificate": "yes",
            "Encrypt": "yes",
        }
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    # If tests set a global session, prefer returning that so in-process
    # request handlers (TestClient) share the same transactional session.
    global _TEST_SESSION  # type: ignore[name-defined]
    try:
        if _TEST_SESSION is not None:
            yield _TEST_SESSION
            return
    except NameError:
        pass

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
_TEST_SESSION = None
