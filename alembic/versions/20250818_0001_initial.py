"""
Initial schema based on SQLAlchemy models.

Revision ID: 20250818_0001
Revises:
Create Date: 2025-08-18
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import mssql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250818_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema dbo is implicit in SQL Server; using schema if needed elsewhere
    op.create_table(
        "Users",
        sa.Column("UserID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("FirstName", sa.String(length=100), nullable=False),
        sa.Column("LastName", sa.String(length=100), nullable=False),
        sa.Column("Email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("HashedPassword", sa.String(length=255), nullable=False),
        sa.Column("DateCreated", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("LastUpdated", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("IsActive", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("EmailVerified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("LastLogin", sa.DateTime(), nullable=True),
        sa.Column("MarkedForDeletion", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        schema="dbo",
    )

    op.create_table(
        "UserSession",
        sa.Column("SessionID", mssql.UNIQUEIDENTIFIER, primary_key=True),
        sa.Column("UserID", sa.Integer(), sa.ForeignKey("dbo.Users.UserID"), nullable=False),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("ExpiresAt", sa.DateTime(), nullable=True),
        sa.Column("IsActive", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("LastSeen", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("IPAddress", sa.String(length=45), nullable=True),
        sa.Column("UserAgent", sa.String(length=255), nullable=True),
        schema="dbo",
    )

    op.create_table(
        "EventType",
        sa.Column("EventTypeID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("Name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("Description", sa.String(length=255), nullable=True),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )

    op.create_table(
        "Event",
        sa.Column("EventID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "EventTypeID", sa.Integer(), sa.ForeignKey("dbo.EventType.EventTypeID"), nullable=True
        ),
        sa.Column("UserID", sa.Integer(), sa.ForeignKey("dbo.Users.UserID"), nullable=False),
        sa.Column("Name", sa.String(length=255), nullable=False),
        sa.Column("Date", sa.DateTime(), nullable=True),
        sa.Column("Code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("Password", sa.String(length=255), nullable=False),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("LastUpdated", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("Published", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("TermsChecked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        schema="dbo",
    )

    op.create_table(
        "Theme",
        sa.Column("ThemeID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("Name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("Description", sa.String(length=255), nullable=True),
        sa.Column("ButtonColour1", sa.String(length=16), nullable=True),
        sa.Column("ButtonColour2", sa.String(length=16), nullable=True),
        sa.Column("BackgroundColour", sa.String(length=16), nullable=True),
        sa.Column("BackgroundImage", sa.String(length=255), nullable=True),
        sa.Column("CoverPhotoPath", sa.String(length=255), nullable=True),
        sa.Column("FontFamily", sa.String(length=64), nullable=True),
        sa.Column("TextColour", sa.String(length=16), nullable=True),
        sa.Column("AccentColour", sa.String(length=16), nullable=True),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )

    op.create_table(
        "EventCustomisation",
        sa.Column("EventCustomisationID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("EventID", sa.Integer(), sa.ForeignKey("dbo.Event.EventID"), nullable=False),
        sa.Column("WelcomeMessage", sa.String(length=255), nullable=True),
        sa.Column("UploadInstructions", sa.String(length=255), nullable=True),
        sa.Column("ThankYouMessage", sa.String(length=255), nullable=True),
        sa.Column("FooterMessage", sa.String(length=255), nullable=True),
        sa.Column("StorageLimitMessage", sa.String(length=255), nullable=True),
        sa.Column("ButtonColour1", sa.String(length=16), nullable=True),
        sa.Column("ButtonColour2", sa.String(length=16), nullable=True),
        sa.Column("BackgroundColour", sa.String(length=16), nullable=True),
        sa.Column("BackgroundImage", sa.String(length=255), nullable=True),
        sa.Column("CoverPhotoPath", sa.String(length=255), nullable=True),
        sa.Column("ThemeID", sa.Integer(), sa.ForeignKey("dbo.Theme.ThemeID"), nullable=True),
        sa.Column("FontFamily", sa.String(length=64), nullable=True),
        sa.Column("TextColour", sa.String(length=16), nullable=True),
        sa.Column("AccentColour", sa.String(length=16), nullable=True),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )

    op.create_table(
        "EventStorage",
        sa.Column("EventStorageID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("EventID", sa.Integer(), sa.ForeignKey("dbo.Event.EventID"), nullable=False),
        sa.Column("StoragePath", sa.String(length=255), nullable=False),
        sa.Column("StorageLimitMB", sa.Integer(), nullable=False),
        sa.Column("CurrentUsageMB", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("LastUploadDateTime", sa.DateTime(), nullable=True),
        sa.Column("IsLocked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )

    op.create_table(
        "GuestSession",
        sa.Column("GuestID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("EventID", sa.Integer(), sa.ForeignKey("dbo.Event.EventID"), nullable=False),
        sa.Column("DeviceType", sa.String(length=64), nullable=True),
        sa.Column("GuestEmail", sa.String(length=255), nullable=True),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UploadCount", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("TermsChecked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        schema="dbo",
    )

    op.create_table(
        "FileMetadata",
        sa.Column("FileMetadataID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("EventID", sa.Integer(), sa.ForeignKey("dbo.Event.EventID"), nullable=False),
        sa.Column(
            "GuestID", sa.Integer(), sa.ForeignKey("dbo.GuestSession.GuestID"), nullable=True
        ),
        sa.Column("FileName", sa.String(length=255), nullable=False),
        sa.Column("FileType", sa.String(length=64), nullable=False),
        sa.Column("FileSize", sa.Integer(), nullable=False),
        sa.Column("CapturedDateTime", sa.DateTime(), nullable=True),
        sa.Column("GPSLat", sa.String(length=32), nullable=True),
        sa.Column("GPSLong", sa.String(length=32), nullable=True),
        sa.Column("Checksum", sa.String(length=128), nullable=True),
        sa.Column("UploadDate", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("Tags", sa.String(length=255), nullable=True),
        sa.Column("Deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )

    op.create_table(
        "EventPlan",
        sa.Column("PlanID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("Name", sa.String(length=100), nullable=False),
        sa.Column("Code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("Description", sa.Text(), nullable=True),
        sa.Column("Features", sa.Text(), nullable=True),
        sa.Column("PriceCents", sa.Integer(), nullable=False),
        sa.Column("Currency", sa.String(length=8), nullable=False, server_default=sa.text("'gbp'")),
        sa.Column("IsActive", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )

    op.create_table(
        "Purchase",
        sa.Column("PurchaseID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("UserID", sa.Integer(), sa.ForeignKey("dbo.Users.UserID"), nullable=False),
        sa.Column("PlanID", sa.Integer(), sa.ForeignKey("dbo.EventPlan.PlanID"), nullable=False),
        sa.Column("Amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("Currency", sa.String(length=8), nullable=False, server_default=sa.text("'GBP'")),
        sa.Column("StripeSessionID", sa.String(length=255), nullable=True),
        sa.Column("StripePaymentIntentID", sa.String(length=255), nullable=True),
        sa.Column(
            "Status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )

    op.create_table(
        "PaymentLog",
        sa.Column("LogID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("UserID", sa.Integer(), sa.ForeignKey("dbo.Users.UserID"), nullable=True),
        sa.Column("EventType", sa.String(length=64), nullable=False),
        sa.Column("StripeEventID", sa.String(length=255), nullable=True),
        sa.Column("Payload", sa.Text(), nullable=True),
        sa.Column("ErrorMessage", sa.Text(), nullable=True),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )


def downgrade() -> None:
    for table in [
        "PaymentLog",
        "Purchase",
        "EventPlan",
        "FileMetadata",
        "GuestSession",
        "EventStorage",
        "EventCustomisation",
        "Theme",
        "Event",
        "EventType",
        "UserSession",
        "Users",
    ]:
        try:
            op.drop_table(table, schema="dbo")
        except Exception:
            # Ignore if already dropped
            pass
