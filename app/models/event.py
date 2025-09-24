from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import synonym
from sqlalchemy.sql import func

from app.models.user import Base


class EventType(Base):
    __tablename__ = "EventType"
    EventTypeID = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(100), nullable=False, unique=True)
    Description = Column(String(255), nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Event(Base):
    __tablename__ = "Event"
    EventID = Column(Integer, primary_key=True, autoincrement=True)
    EventTypeID = Column(Integer, ForeignKey("EventType.EventTypeID"), nullable=True)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    Name = Column(String(255), nullable=False)
    Date = Column(DateTime, nullable=True)
    Code = Column(String(32), nullable=False, unique=True)
    Password = Column(String(255), nullable=False)
    CreatedAt = Column(DateTime, server_default=func.now())
    LastUpdated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    Published = Column(Boolean, default=False)
    TermsChecked = Column(Boolean, default=False)
    IsDateLocked = Column(Boolean, default=False)
    DateLockedAt = Column(DateTime, nullable=True)


class EventCustomisation(Base):
    __tablename__ = "EventCustomisation"
    EventCustomisationID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    WelcomeMessage = Column(String(255), nullable=True)
    UploadInstructions = Column(String(255), nullable=True)
    ThankYouMessage = Column(String(255), nullable=True)
    FooterMessage = Column(String(255), nullable=True)
    StorageLimitMessage = Column(String(255), nullable=True)
    ButtonColour1 = Column(String(16), nullable=True)
    ButtonColour2 = Column(String(16), nullable=True)
    BackgroundColour = Column(String(16), nullable=True)
    BackgroundImage = Column(String(255), nullable=True)
    CoverPhotoPath = Column(String(255), nullable=True)
    ThemeID = Column(Integer, ForeignKey("Theme.ThemeID"), nullable=True)
    FontFamily = Column(String(64), nullable=True)
    TextColour = Column(String(16), nullable=True)
    AccentColour = Column(String(32), nullable=True)
    # QR custom colours
    QRFillColour = Column(String(16), nullable=True)
    QRBackColour = Column(String(16), nullable=True)
    # Allow owners (ultimate) to opt-out of website logo being applied to QR codes
    RemoveWebsiteLogo = Column(Boolean, default=False)
    # New lightweight customization options
    ButtonStyle = Column(String(16), nullable=True)  # 'gradient' or 'solid'
    # Optional gradient parameters when ButtonStyle == 'gradient'
    ButtonGradientStyle = Column(String(16), nullable=True)  # 'linear' | 'radial'
    ButtonGradientDirection = Column(String(16), nullable=True)  # e.g., '90deg', '45deg'
    CornerRadius = Column(String(16), nullable=True)  # 'subtle' | 'rounded' | 'sharp'
    ShowCover = Column(Boolean, default=True)
    HeadingSize = Column(String(8), nullable=True)  # 's' | 'm' | 'l'
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Theme(Base):
    __tablename__ = "Theme"
    ThemeID = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(100), nullable=False, unique=True)
    Description = Column(String(255), nullable=True)
    IsActive = Column(Boolean, default=True)
    ButtonColour1 = Column(String(16), nullable=True)
    ButtonColour2 = Column(String(16), nullable=True)
    ButtonStyle = Column(String(16), nullable=True)  # 'gradient' | 'solid'
    BackgroundColour = Column(String(16), nullable=True)
    BackgroundImage = Column(String(255), nullable=True)
    CoverPhotoPath = Column(String(255), nullable=True)
    FontFamily = Column(String(64), nullable=True)
    TextColour = Column(String(16), nullable=True)
    AccentColour = Column(String(32), nullable=True)
    InputBackgroundColour = Column(String(16), nullable=True)
    DropzoneBackgroundColour = Column(String(16), nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EventStorage(Base):
    __tablename__ = "EventStorage"
    EventStorageID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    StoragePath = Column(String(255), nullable=False)
    StorageLimitMB = Column(Integer, nullable=False)
    CurrentUsageMB = Column(Integer, nullable=False, default=0)
    LastUploadDateTime = Column(DateTime, nullable=True)
    IsLocked = Column(Boolean, default=False)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FileMetadata(Base):
    __tablename__ = "FileMetadata"
    FileMetadataID = Column(Integer, primary_key=True, autoincrement=True)
    # Backwards-compatible alias: some code expects `FileID`
    # Use an ORM synonym instead of reusing the Column object which triggers
    # SQLAlchemy warnings about duplicate Column objects.
    FileID = synonym("FileMetadataID")
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    GuestID = Column(Integer, ForeignKey("GuestSession.GuestID"), nullable=True)
    FileName = Column(String(255), nullable=False)
    FileType = Column(String(64), nullable=False)
    FileSize = Column(Integer, nullable=False)  # Size in bytes
    CapturedDateTime = Column(DateTime, nullable=True)
    GPSLat = Column(String(32), nullable=True)
    GPSLong = Column(String(32), nullable=True)
    Checksum = Column(String(128), nullable=True)
    UploadDate = Column(DateTime, server_default=func.now())
    Tags = Column(String(255), nullable=True)
    Deleted = Column(Boolean, default=False)
    DeletedAt = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FavoriteFile(Base):
    __tablename__ = "FavoriteFile"
    FavoriteID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    FileMetadataID = Column(Integer, ForeignKey("FileMetadata.FileMetadataID"), nullable=False)
    CreatedAt = Column(DateTime, server_default=func.now())


class GuestSession(Base):
    __tablename__ = "GuestSession"
    GuestID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    DeviceType = Column(String(64), nullable=True)
    GuestEmail = Column(String(255), nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
    UploadCount = Column(Integer, default=0)
    TermsChecked = Column(Boolean, default=False)


class EventLockAudit(Base):
    __tablename__ = "EventLockAudit"
    AuditID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=True)
    LockedAt = Column(DateTime, server_default=func.now())
    ClientIP = Column(String(45), nullable=True)
    UserAgent = Column(String(255), nullable=True)
    RequestID = Column(String(64), nullable=True)
    OldDate = Column(DateTime, nullable=True)
    NewDate = Column(DateTime, nullable=True)


class ThemeAudit(Base):
    __tablename__ = "ThemeAudit"
    AuditID = Column(Integer, primary_key=True, autoincrement=True)
    ThemeID = Column(Integer, ForeignKey("Theme.ThemeID"), nullable=False)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=True)
    ChangedAt = Column(DateTime, server_default=func.now())
    ClientIP = Column(String(45), nullable=True)
    UserAgent = Column(String(255), nullable=True)
    RequestID = Column(String(64), nullable=True)
    Changes = Column(String(4000), nullable=True)  # JSON string of field diffs


class EventChecklist(Base):
    __tablename__ = "EventChecklist"
    EventChecklistID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    SharedOnce = Column(Boolean, default=False)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EventTask(Base):
    __tablename__ = "EventTask"
    EventTaskID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    UserID = Column(Integer, ForeignKey("dbo.Users.UserID"), nullable=False)
    Key = Column(String(64), nullable=False)
    State = Column(String(32), nullable=False, default="pending")
    CompletedAt = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())


class GuestMessage(Base):
    __tablename__ = "GuestMessage"
    GuestMessageID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    GuestSessionID = Column(Integer, ForeignKey("GuestSession.GuestID"), nullable=True)
    DisplayName = Column(String(80), nullable=True)
    Message = Column(String(300), nullable=False)
    CreatedAt = Column(DateTime, server_default=func.now())
    Deleted = Column(Boolean, default=False)


class CustomEventType(Base):
    __tablename__ = "CustomEventType"
    CustomEventTypeID = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("Event.EventID"), nullable=False)
    EventTypeID = Column(Integer, ForeignKey("EventType.EventTypeID"), nullable=True)
    CustomEventName = Column(String(255), nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())
