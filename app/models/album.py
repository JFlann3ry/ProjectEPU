from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from .user import Base


class Album(Base):
    __tablename__ = 'Album'
    AlbumID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey('Event.EventID'), nullable=False)
    Name = Column(String(255), nullable=False)
    Description = Column(String(1024), nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())

    photos = relationship('AlbumPhoto', back_populates='album', cascade='all, delete-orphan')


class AlbumPhoto(Base):
    __tablename__ = 'AlbumPhoto'
    AlbumPhotoID = Column(Integer, primary_key=True, autoincrement=True)
    AlbumID = Column(Integer, ForeignKey('Album.AlbumID'), nullable=False)
    # FileID maps to FileMetadata.FileMetadataID (alias on FileMetadata for compatibility)
    FileID = Column(Integer, ForeignKey('FileMetadata.FileMetadataID'), nullable=False)
    Ordinal = Column(Integer, nullable=True)

    album = relationship('Album', back_populates='photos')
    file = relationship('FileMetadata')
