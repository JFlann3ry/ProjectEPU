"""
Create Album and AlbumPhoto tables directly using SQLAlchemy metadata.
This script is a one-off to ensure the schema exists when Alembic can't apply migrations
because of multiple heads. It will create the two tables if they don't exist.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table
from sqlalchemy.sql import func

from db import engine

meta = MetaData()

album = Table(
    'Album',
    meta,
    Column('AlbumID', Integer, primary_key=True, autoincrement=True),
    Column('EventID', Integer, ForeignKey('Event.EventID'), nullable=False),
    Column('Name', String(255), nullable=False),
    Column('Description', String(1024), nullable=True),
    Column('CreatedAt', DateTime, server_default=func.now()),
    schema='dbo'
)

album_photo = Table(
    'AlbumPhoto',
    meta,
    Column('AlbumPhotoID', Integer, primary_key=True, autoincrement=True),
    Column('AlbumID', Integer, ForeignKey('Album.AlbumID'), nullable=False),
    Column('FileID', Integer, ForeignKey('FileMetadata.FileID'), nullable=False),
    Column('Ordinal', Integer, nullable=True),
    schema='dbo'
)

if __name__ == '__main__':
    print('Creating Album tables if missing...')
    meta.bind = engine
    meta.create_all(tables=[album, album_photo])
    print('Done.')
