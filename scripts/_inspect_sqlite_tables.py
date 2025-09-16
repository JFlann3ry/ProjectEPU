import os
os.environ['TEST_SQLITE'] = '1'
from sqlalchemy import text

# Force sqlite inspection mode for this script
os.environ["TEST_SQLITE"] = "1"

from db import engine

# Import many models to register tables with SQLAlchemy metadata.
# These imports may be unused directly in this script but are required to
# register table classes on the metadata object.
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


def main() -> None:
    print("before strip keys sample=", list(UserBase.metadata.tables.keys())[:60])

    # Strip schema so create_all works against sqlite memory DB
    for tbl in list(UserBase.metadata.tables.values()):
        try:
            tbl.schema = None
        except Exception:
            # ignore any tables that don't support schema modification
            pass

    print("after strip keys sample=", list(UserBase.metadata.tables.keys())[:60])
    print("creating tables")
    UserBase.metadata.create_all(bind=engine)

    conn = engine.connect()
    res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
    created = [row[0] for row in res.fetchall()]
    print("sqlite tables created:", created)
    conn.close()


if __name__ == "__main__":
    main()

