"""
Add Album and AlbumPhoto tables.

Revision ID: 20250912_0019
Revises: 20250911_0023
Create Date: 2025-09-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250912_0019"
down_revision = "20250911_0023_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.create_table(
            "Album",
            sa.Column("AlbumID", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("EventID", sa.Integer(), sa.ForeignKey("Event.EventID"), nullable=False),
            sa.Column("Name", sa.String(length=255), nullable=False),
            sa.Column("Description", sa.String(length=1024), nullable=True),
            sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
            schema="dbo",
        )
    except Exception:
        pass

    try:
        op.create_table(
            "AlbumPhoto",
            sa.Column("AlbumPhotoID", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("AlbumID", sa.Integer(), sa.ForeignKey("Album.AlbumID"), nullable=False),
            sa.Column("FileID", sa.Integer(), sa.ForeignKey("FileMetadata.FileID"), nullable=False),
            sa.Column("Ordinal", sa.Integer(), nullable=True),
            schema="dbo",
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_table("AlbumPhoto", schema="dbo")
    except Exception:
        pass
    try:
        op.drop_table("Album", schema="dbo")
    except Exception:
        pass
