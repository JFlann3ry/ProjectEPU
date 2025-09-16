import sys

from sqlalchemy import text

# Ensure project root on path for local imports
sys.path.insert(0, r'e:\ProjectEPU')
from db import engine

create_album_sql = (
    "IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Album') "
    "AND type in (N'U'))\n"
    "BEGIN\n"
    "    CREATE TABLE dbo.Album (\n"
    "        AlbumID INT IDENTITY(1,1) PRIMARY KEY,\n"
    "        EventID INT NOT NULL,\n"
    "        Name NVARCHAR(255) NOT NULL,\n"
    "        Description NVARCHAR(1024) NULL,\n"
    "        CreatedAt DATETIME NULL DEFAULT (GETDATE())\n"
    "    );\n"
    "END\n"
)

create_albumphoto_sql = (
    "IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.AlbumPhoto') "
    "AND type in (N'U'))\n"
    "BEGIN\n"
    "    CREATE TABLE dbo.AlbumPhoto (\n"
    "        AlbumPhotoID INT IDENTITY(1,1) PRIMARY KEY,\n"
    "        AlbumID INT NOT NULL,\n"
    "        FileID INT NOT NULL,\n"
    "        Ordinal INT NULL\n"
    "    );\n"
    "END\n"
)

with engine.connect() as conn:
    conn.execute(text(create_album_sql))
    conn.execute(text(create_albumphoto_sql))
    conn.commit()

print('Created/ensured Album and AlbumPhoto tables (if using MSSQL).')
