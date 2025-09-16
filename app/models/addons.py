from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.models.user import Base


class AddonCatalog(Base):
    __tablename__ = "AddonCatalog"
    __table_args__ = {"schema": "dbo"}
    AddonID = Column(Integer, primary_key=True, autoincrement=True)
    Code = Column(String(50), nullable=False, unique=True)
    Name = Column(String(120), nullable=False)
    Description = Column(Text, nullable=True)
    PriceCents = Column(Integer, nullable=False, default=0)
    Currency = Column(String(8), nullable=False, default="gbp")
    AllowQuantity = Column(Boolean, default=False)
    MinQuantity = Column(Integer, nullable=False, default=1)
    MaxQuantity = Column(Integer, nullable=False, default=1)
    IsActive = Column(Boolean, default=True)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EventAddonPurchase(Base):
    __tablename__ = "EventAddonPurchase"
    __table_args__ = {"schema": "dbo"}
    PurchaseID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=True)
    AddonID = Column(Integer, ForeignKey("dbo.AddonCatalog.AddonID"), nullable=False)
    Quantity = Column(Integer, nullable=False, default=1)
    Amount = Column(Numeric(10, 2), nullable=False)
    Currency = Column(String(8), nullable=False, default="GBP")
    StripeSessionID = Column(String(255), nullable=True)
    StripePaymentIntentID = Column(String(255), nullable=True)
    Status = Column(String(32), nullable=False, default="pending")
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())
