from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func

from app.models.user import Base


class EventGalleryOrder(Base):
    __tablename__ = "EventGalleryOrder"
    EventGalleryOrderID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    FileMetadataID = Column(Integer, ForeignKey("FileMetadata.FileMetadataID"), nullable=False)
    Ordinal = Column(Integer, nullable=False)
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("EventID", "Ordinal", name="uq_event_ordinal"),
        UniqueConstraint("EventID", "FileMetadataID", name="uq_event_file"),
    )
