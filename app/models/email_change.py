from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

# Use the application's shared Base so models share metadata
from app.models.user import Base


class EmailChangeRequest(Base):
    __tablename__ = "EmailChangeRequests"
    __table_args__ = {"schema": "dbo"}
    ID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    OldEmail = Column(String(255), nullable=False)
    NewEmail = Column(String(255), nullable=False)
    Token = Column(String(512), nullable=False, unique=True)
    CreatedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    ExpiresAt = Column(DateTime, nullable=True)
    CompletedAt = Column(DateTime, nullable=True)
    ReversedAt = Column(DateTime, nullable=True)
    IsActive = Column(Boolean, default=True)
