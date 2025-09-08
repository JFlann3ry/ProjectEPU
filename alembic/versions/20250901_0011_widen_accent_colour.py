"""
Widen AccentColour columns to length 32 for rgba values.

Revision ID: 20250901_0011
Revises: 20250901_0010
Create Date: 2025-09-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "20250901_0011"
down_revision = "20250901_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.alter_column(
            "Theme",
            "AccentColour",
            existing_type=sa.String(length=16),
            type_=sa.String(length=32),
            existing_nullable=True,
            schema="dbo",
        )
    except Exception:
        pass
    try:
        op.alter_column(
            "EventCustomisation",
            "AccentColour",
            existing_type=sa.String(length=16),
            type_=sa.String(length=32),
            existing_nullable=True,
            schema="dbo",
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.alter_column(
            "EventCustomisation",
            "AccentColour",
            existing_type=sa.String(length=32),
            type_=sa.String(length=16),
            existing_nullable=True,
            schema="dbo",
        )
    except Exception:
        pass
    try:
        op.alter_column(
            "Theme",
            "AccentColour",
            existing_type=sa.String(length=32),
            type_=sa.String(length=16),
            existing_nullable=True,
            schema="dbo",
        )
    except Exception:
        pass
