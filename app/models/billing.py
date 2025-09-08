from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.models.user import Base


class Purchase(Base):
    __tablename__ = "Purchase"
    PurchaseID = Column(Integer, primary_key=True, autoincrement=True)
    # Ensure schema-qualified FK for consistency with Users table
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    PlanID = Column(Integer, ForeignKey("EventPlan.PlanID"), nullable=False)
    Amount = Column(Numeric(10, 2), nullable=False)
    Currency = Column(String(8), nullable=False, default="GBP")
    StripeSessionID = Column(String(255), nullable=True)
    StripePaymentIntentID = Column(String(255), nullable=True)
    Status = Column(String(32), nullable=False, default="pending")
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PaymentLog(Base):
    __tablename__ = "PaymentLog"
    LogID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=True)
    EventType = Column(String(64), nullable=False)
    StripeEventID = Column(String(255), nullable=True)
    Payload = Column(Text, nullable=True)
    ErrorMessage = Column(Text, nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
