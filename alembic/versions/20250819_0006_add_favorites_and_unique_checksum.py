"""
Add FavoriteFile table and indexes for duplicate detection.

Revision ID: 20250819_0006
Revises: 20250819_0005
Create Date: 2025-08-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "20250819_0006"
down_revision = "20250819_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Favorite table
    op.create_table(
        "FavoriteFile",
        sa.Column("FavoriteID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("UserID", sa.Integer(), sa.ForeignKey("dbo.Users.UserID"), nullable=False),
        sa.Column(
            "FileMetadataID",
            sa.Integer(),
            sa.ForeignKey("dbo.FileMetadata.FileMetadataID"),
            nullable=False,
        ),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        schema="dbo",
    )
    # Helpful indexes for duplicate detection and lookups
    try:
        op.create_index(
            "IX_FileMetadata_Event_Checksum",
            "FileMetadata",
            ["EventID", "Checksum"],
            unique=False,
            schema="dbo",
        )
    except Exception:
        pass
    try:
        op.create_index(
            "IX_FavoriteFile_User_File",
            "FavoriteFile",
            ["UserID", "FileMetadataID"],
            unique=True,
            schema="dbo",
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index("IX_FavoriteFile_User_File", table_name="FavoriteFile", schema="dbo")
    except Exception:
        pass
    try:
        op.drop_index("IX_FileMetadata_Event_Checksum", table_name="FileMetadata", schema="dbo")
    except Exception:
        pass
    try:
        op.drop_table("FavoriteFile", schema="dbo")
    except Exception:
        pass
