import sys

from sqlalchemy import text

sys.path.insert(0, r'e:\ProjectEPU')
from db import engine

create_album_sql = '''
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Album') AND type in (N'U'))
BEGIN
    CREATE TABLE dbo.Album (
        AlbumID INT IDENTITY(1,1) PRIMARY KEY,
        EventID INT NOT NULL,
        Name NVARCHAR(255) NOT NULL,
        Description NVARCHAR(1024) NULL,
        CreatedAt DATETIME NULL DEFAULT (GETDATE())
    );
END
'''

create_albumphoto_sql = '''
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.AlbumPhoto') AND type in (N'U'))
BEGIN
    CREATE TABLE dbo.AlbumPhoto (
        AlbumPhotoID INT IDENTITY(1,1) PRIMARY KEY,
        AlbumID INT NOT NULL,
        FileID INT NOT NULL,
        Ordinal INT NULL
    );
END
'''

with engine.connect() as conn:
    conn.execute(text(create_album_sql))
    conn.execute(text(create_albumphoto_sql))
    conn.commit()
print('Created/ensured Album and AlbumPhoto tables (if using MSSQL).')
