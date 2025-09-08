"""
Add IsDateLocked and DateLockedAt to Event.

Revision ID: 20250819_0004
Revises: 20250819_0003
Create Date: 2025-08-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250819_0004"
down_revision = "20250819_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("Event", schema="dbo") as batch_op:
        batch_op.add_column(
            sa.Column("IsDateLocked", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("DateLockedAt", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("Event", schema="dbo") as batch_op:
        batch_op.drop_column("DateLockedAt")
        batch_op.drop_column("IsDateLocked")
