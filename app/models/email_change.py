from datetime import datetime, timezone

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


def utc_now_naive_utc():
    """Return current UTC time as a naive datetime (tzinfo removed).

    Avoids deprecated datetime.utcnow() while keeping stored values consistent
    with existing naive UTC columns.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmailChangeRequest(Base):
    __tablename__ = "EmailChangeRequests"
    __table_args__ = {"schema": "dbo"}
    ID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    OldEmail = Column(String(255), nullable=False)
    NewEmail = Column(String(255), nullable=False)
    Token = Column(String(512), nullable=False, unique=True)
    CreatedAt = Column(DateTime, nullable=False, default=utc_now_naive_utc)
    ExpiresAt = Column(DateTime, nullable=True)
    CompletedAt = Column(DateTime, nullable=True)
    ReversedAt = Column(DateTime, nullable=True)
    IsActive = Column(Boolean, default=True)
