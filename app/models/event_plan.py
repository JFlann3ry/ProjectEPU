from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.user import Base


class EventPlan(Base):
    __tablename__ = "EventPlan"
    PlanID = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(100), nullable=False)
    Code = Column(String(32), nullable=False, unique=True)
    Description = Column(Text, nullable=True)
    Features = Column(Text, nullable=True)  # JSON string
    PriceCents = Column(Integer, nullable=False)
    Currency = Column(String(8), nullable=False, default="gbp")
    IsActive = Column(Boolean, default=True)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())
