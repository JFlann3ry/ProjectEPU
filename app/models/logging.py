from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.user import Base


class AppErrorLog(Base):
    __tablename__ = "AppErrorLog"
    ErrorID = Column(Integer, primary_key=True, autoincrement=True)
    OccurredAt = Column(DateTime, server_default=func.now())
    RequestID = Column(String(64), nullable=True)
    Path = Column(String(500), nullable=True)
    Method = Column(String(16), nullable=True)
    StatusCode = Column(Integer, nullable=True)
    UserID = Column(Integer, nullable=True)
    ClientIP = Column(String(45), nullable=True)
    UserAgent = Column(String(255), nullable=True)
    Referer = Column(String(500), nullable=True)
    Message = Column(Text, nullable=True)
    StackTrace = Column(Text, nullable=True)


class JobRunLog(Base):
    __tablename__ = "JobRunLog"
    JobRunLogID = Column(Integer, primary_key=True, autoincrement=True)
    JobName = Column(String(255), nullable=False)
    StepName = Column(String(255), nullable=True)
    StartedAt = Column(DateTime, nullable=False)
    FinishedAt = Column(DateTime, nullable=False)
    Succeeded = Column(Integer, default=0, nullable=False)  # 0=failed, 1=succeeded
    Details = Column(Text, nullable=True)  # JSON or free-form details
    CreatedAt = Column(DateTime, server_default=func.now(), nullable=False)
