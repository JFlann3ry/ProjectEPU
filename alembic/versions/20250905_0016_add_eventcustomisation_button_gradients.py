"""
Add ButtonGradientStyle and ButtonGradientDirection to EventCustomisation.

Revision ID: 20250905_0016
Revises: 20250905_0015
Create Date: 2025-09-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "20250905_0016"
down_revision = "20250905_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add two optional gradient-related columns used when ButtonStyle == 'gradient'
    try:
        op.add_column(
            "EventCustomisation",
            sa.Column("ButtonGradientStyle", sa.String(length=16), nullable=True),
            schema="dbo",
        )
    except Exception:
        # Column might already exist in some environments
        pass
    try:
        op.add_column(
            "EventCustomisation",
            sa.Column("ButtonGradientDirection", sa.String(length=16), nullable=True),
            schema="dbo",
        )
    except Exception:
        pass


def downgrade() -> None:
    for col in ("ButtonGradientDirection", "ButtonGradientStyle"):
        try:
            op.drop_column("EventCustomisation", col, schema="dbo")
        except Exception:
            pass
