"""
Add customization columns to EventCustomisation: ButtonStyle, CornerRadius, ShowCover, HeadingSize.

Revision ID: 20250819_0007
Revises: 20250819_0006
Create Date: 2025-08-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "20250819_0007"
down_revision = "20250819_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column(
            "EventCustomisation",
            sa.Column("ButtonStyle", sa.String(length=16), nullable=True),
            schema="dbo",
        )
    except Exception:
        pass
    try:
        op.add_column(
            "EventCustomisation",
            sa.Column("CornerRadius", sa.String(length=16), nullable=True),
            schema="dbo",
        )
    except Exception:
        pass
    try:
        op.add_column(
            "EventCustomisation",
            sa.Column(
                "ShowCover", sa.Boolean(), server_default=sa.sql.expression.true(), nullable=False
            ),
            schema="dbo",
        )
    except Exception:
        pass
    try:
        op.add_column(
            "EventCustomisation",
            sa.Column("HeadingSize", sa.String(length=8), nullable=True),
            schema="dbo",
        )
    except Exception:
        pass


def downgrade() -> None:
    for col in ("HeadingSize", "ShowCover", "CornerRadius", "ButtonStyle"):
        try:
            op.drop_column("EventCustomisation", col, schema="dbo")
        except Exception:
            pass
