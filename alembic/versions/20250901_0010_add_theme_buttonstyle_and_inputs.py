"""
Add ButtonStyle, InputBackgroundColour, DropzoneBackgroundColour to Theme.

Revision ID: 20250901_0010
Revises: 20250822_0008_add_theme_audit
Create Date: 2025-09-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "20250901_0010"
down_revision = "20250901_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column(
            "Theme", sa.Column("ButtonStyle", sa.String(length=16), nullable=True), schema="dbo"
        )
    except Exception:
        pass
    try:
        op.add_column(
            "Theme",
            sa.Column("InputBackgroundColour", sa.String(length=16), nullable=True),
            schema="dbo",
        )
    except Exception:
        pass
    try:
        op.add_column(
            "Theme",
            sa.Column("DropzoneBackgroundColour", sa.String(length=16), nullable=True),
            schema="dbo",
        )
    except Exception:
        pass


def downgrade() -> None:
    for col in ("DropzoneBackgroundColour", "InputBackgroundColour", "ButtonStyle"):
        try:
            op.drop_column("Theme", col, schema="dbo")
        except Exception:
            pass
