import sqlalchemy as sa

from db import engine


def main():
    with engine.connect() as conn:
        res = conn.execute(
            sa.text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'EventGalleryOrder'")
        )
        rows = [r[0] for r in res.fetchall()]
        print("found" if rows else "missing")


if __name__ == "__main__":
    main()
