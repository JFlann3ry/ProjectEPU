import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as _Session

from db import engine

# If tests use the in-memory sqlite (TEST_SQLITE=1), ensure schema exists by
# creating all models' tables on the engine before tests run.
if os.getenv("TEST_SQLITE") == "1":
    try:
        # Import model modules so their Table objects are registered on Base.metadata
        import app.models as models_pkg  # noqa: F401
        import app.models.addons  # noqa: F401
        import app.models.billing  # noqa: F401
        import app.models.event  # noqa: F401
        import app.models.event_plan  # noqa: F401
        import app.models.export  # noqa: F401
        import app.models.logging  # noqa: F401
        import app.models.user  # noqa: F401
        import app.models.user_prefs  # noqa: F401
        from app.models.user import Base as UserBase

        try:
            print("[conftest] metadata tables before strip:", list(UserBase.metadata.tables.keys()))
        except Exception:
            print("[conftest] could not list metadata tables before strip")

        # For in-memory SQLite tests, remove schema names from Table objects so
        # SQLAlchemy doesn't compile queries with `dbo.` prefixes. Then create
        # all tables using the application's metadata (now schema-less).
        try:
            tbls = list(UserBase.metadata.tables.values())
            for tbl in tbls:
                try:
                    tbl.schema = None
                except Exception:
                    # non-table or immutable, skip
                    continue

            print("[conftest] creating tables via UserBase.metadata (schema cleared)")
            UserBase.metadata.create_all(bind=engine)

            # Diagnostics: list sqlite tables if using sqlite
            try:
                if engine.dialect.name == "sqlite":
                    from sqlalchemy import text

                    conn = engine.connect()
                    res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                    created = [row[0] for row in res.fetchall()]
                    conn.close()
                    print("[conftest] sqlite tables created:", created)
            except Exception as e:
                print("[conftest] failed to list sqlite_master:", e)
        except Exception as e:
            import traceback

            print("[conftest] error while creating tables:")
            traceback.print_exception(type(e), e, e.__traceback__)
    except Exception as e:
        import traceback

        print("[conftest] exception during TEST_SQLITE setup:")
        traceback.print_exception(type(e), e, e.__traceback__)


@pytest.fixture
def client():
    # Import the app here so the TEST_SQLITE pre-setup above runs before the
    # application and its startup code are imported.
    from main import app

    return TestClient(app)


@pytest.fixture
def db_session():
    """Provide a SQLAlchemy Session for tests using a transactional, connection-bound session.

    This pattern ensures each test runs inside a DB transaction that is rolled back at teardown,
    keeping tests isolated and avoiding persistent test data.
    """
    # Connect and start a transaction
    connection = engine.connect()
    transaction = connection.begin()

    # Bind a session to the connection
    session = _Session(bind=connection)
    # expose to db.get_db
    try:
        import db as dbmod

        dbmod._TEST_SESSION = session
    except Exception:
        pass

    try:
        yield session
    finally:
        # rollback any changes and close everything
        try:
            session.rollback()
        except Exception:
            pass
        session.close()
        try:
            import db as dbmod

            dbmod._TEST_SESSION = None
        except Exception:
            pass
        try:
            transaction.rollback()
        except Exception:
            # If already rolled back/committed, ignore
            pass
        connection.close()


@pytest.fixture(autouse=True)
def ensure_test_user(db_session):
    """Create a minimal test user with UserID=1 if not present so tests that assume it pass.

    Runs inside the same transactional session so data will be rolled back after each test.
    """
    try:
        from app.models.user import Users

        existing = db_session.query(Users).filter(Users.UserID == 1).first()
        if not existing:
            u = Users(Email='testuser@example.com', PasswordHash='x', CreatedAt=None)
            # If Users.UserID is autoincrement, we can't force ID reliably across DBs; try to insert and leave it.
            db_session.add(u)
            db_session.flush()
    except Exception:
        # If Users model or table isn't available in this test environment, ignore silently.
        pass
