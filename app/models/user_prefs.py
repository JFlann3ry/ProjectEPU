from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from app.models.user import Base


class UserEmailPreference(Base):
    __tablename__ = "UserEmailPreference"
    __table_args__ = (
        UniqueConstraint("UserID", name="UQ_UserEmailPreference_UserID"),
        {"schema": "dbo"},
    )

    PreferenceID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    MarketingOptIn = Column(Boolean, nullable=False, server_default="0")
    ProductUpdatesOptIn = Column(Boolean, nullable=False, server_default="0")
    EventRemindersOptIn = Column(Boolean, nullable=False, server_default="1")
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())
