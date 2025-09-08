import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import declarative_base, deferred
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "Users"
    __table_args__ = {"schema": "dbo"}
    UserID = Column(Integer, primary_key=True, autoincrement=True)
    FirstName = Column(String(100), nullable=False)
    LastName = Column(String(100), nullable=False)
    Email = Column(String(255), nullable=False, unique=True)
    HashedPassword = Column(String(255), nullable=False)
    DateCreated = Column(DateTime, server_default=func.now())
    LastUpdated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    IsActive = Column(Boolean, default=True)
    EmailVerified = Column(Boolean, default=False)
    LastLogin = Column(DateTime, nullable=True)
    MarkedForDeletion = Column(Boolean, default=False)
    # Admin role flag (replaces hard-coded user id checks)
    # Deferred to avoid selecting the column if the DB hasn't been migrated yet.
    IsAdmin = deferred(Column(Boolean, default=False))


class UserSession(Base):
    __tablename__ = "UserSession"
    SessionID = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    CreatedAt = Column(DateTime, server_default=func.now())
    ExpiresAt = Column(DateTime, nullable=True)
    IsActive = Column(Boolean, default=True)
    LastSeen = Column(DateTime, server_default=func.now())
    IPAddress = Column(String(45), nullable=True)
    UserAgent = Column(String(255), nullable=True)
