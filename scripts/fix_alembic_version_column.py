"""Fix alembic_version.version_num column length for SQL Server.

This script connects to the project's DB using the existing `db.engine`
and alters the `alembic_version.version_num` column to NVARCHAR(255) so
long human-readable revision identifiers won't be truncated.

Run with the project's virtualenv python.
"""
from sqlalchemy import text

from db import engine


def main() -> None:
    # Drop the primary key constraint that references the version_num column
    # then alter the column to NVARCHAR(255) and recreate the PK. This is
    # necessary on SQL Server when the PK depends on the column being altered.
    drop_pk = "IF EXISTS (SELECT 1 FROM sys.objects WHERE name = 'alembic_version_pkc') BEGIN ALTER TABLE dbo.alembic_version DROP CONSTRAINT alembic_version_pkc END"
    alter_col = "ALTER TABLE dbo.alembic_version ALTER COLUMN version_num NVARCHAR(255) NOT NULL;"
    create_pk = "ALTER TABLE dbo.alembic_version ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);"

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text(drop_pk))
            conn.execute(text(alter_col))
            conn.execute(text(create_pk))
            trans.commit()
        except Exception:
            trans.rollback()
            raise

    print("alembic_version.version_num column altered to NVARCHAR(255) and PK recreated")


if __name__ == "__main__":
    main()
