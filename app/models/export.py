from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.models.user import Base


class UserDataExportJob(Base):
    __tablename__ = "UserDataExportJob"
    __table_args__ = {"schema": "dbo"}

    JobID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    Status = Column(String(16), nullable=False, default="queued")  # queued|running|completed|failed
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())
    CompletedAt = Column(DateTime, nullable=True)
    ExpiresAt = Column(DateTime, nullable=True)
    FilePath = Column(String(500), nullable=True)  # Absolute path to ZIP on disk
    ErrorMessage = Column(Text, nullable=True)
