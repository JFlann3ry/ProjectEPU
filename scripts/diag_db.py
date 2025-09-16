import os
import pathlib
import sys


def main() -> None:
    # Ensure project root is on sys.path so top-level imports (like `db`) work
    root = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    from app.models.user import Base
    from db import engine

    print('TEST_SQLITE=', os.getenv('TEST_SQLITE'))

    print('engine.url =', getattr(engine, 'url', None))
    print('metadata keys =', list(Base.metadata.tables.keys()))
    for k, t in Base.metadata.tables.items():
        print(' -', k, 'schema=', getattr(t, 'schema', None))

    print('\nRunning Base.metadata.create_all(bind=engine)')
    Base.metadata.create_all(bind=engine)

    # list sqlite_master
    conn = engine.connect()
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table'"
    ).fetchall()
    print('\nsqlite_master tables:')
    for r in rows:
        print('  ', r[0])
    conn.close()


if __name__ == '__main__':
    main()
