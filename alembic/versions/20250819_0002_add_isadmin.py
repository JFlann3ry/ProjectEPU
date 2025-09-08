"""
Add IsAdmin flag to Users.

Revision ID: 20250819_0002
Revises: 20250818_0001
Create Date: 2025-08-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250819_0002"
down_revision = "20250818_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("Users", schema="dbo") as batch_op:
        batch_op.add_column(
            sa.Column("IsAdmin", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )


def downgrade() -> None:
    with op.batch_alter_table("Users", schema="dbo") as batch_op:
        try:
            batch_op.drop_column("IsAdmin")
        except Exception:
            pass
