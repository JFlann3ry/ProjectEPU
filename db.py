from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings

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

engine = create_engine(connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
