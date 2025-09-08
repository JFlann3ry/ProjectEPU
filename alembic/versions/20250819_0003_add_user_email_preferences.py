"""
Create UserEmailPreference table.

Revision ID: 20250819_0003
Revises: 20250819_0002
Create Date: 2025-08-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250819_0003"
down_revision = "20250819_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "UserEmailPreference",
        sa.Column("PreferenceID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("UserID", sa.Integer(), nullable=False),
        sa.Column("MarketingOptIn", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("ProductUpdatesOptIn", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("EventRemindersOptIn", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["UserID"], ["dbo.Users.UserID"]),
        sa.UniqueConstraint("UserID", name="UQ_UserEmailPreference_UserID"),
        schema="dbo",
    )


def downgrade() -> None:
    try:
        op.drop_table("UserEmailPreference", schema="dbo")
    except Exception:
        pass
