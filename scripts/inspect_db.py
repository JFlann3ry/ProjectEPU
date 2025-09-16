import db
from app.models.user import Base

print('metadata keys:', list(Base.metadata.tables.keys()))
print('engine URL:', getattr(db.engine, 'url', None))
Base.metadata.create_all(bind=db.engine)
conn = db.engine.connect()
res = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('sqlite tables:', [r[0] for r in res])
conn.close()
