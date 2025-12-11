from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.user import Base


class RateLimitCounter(Base):
    __tablename__ = "RateLimitCounter"
    __table_args__ = {"schema": "dbo"}

    Key = Column(String(255), primary_key=True)
    Window = Column(Integer, primary_key=True)
    Count = Column(Integer, nullable=False, default=0)
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())