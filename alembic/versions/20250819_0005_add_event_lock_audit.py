"""
Add EventLockAudit table to track event date locks.

Revision ID: 20250819_0005
Revises: 20250819_0004
Create Date: 2025-08-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "20250819_0005"
down_revision = "20250819_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "EventLockAudit",
        sa.Column("AuditID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("EventID", sa.Integer(), sa.ForeignKey("dbo.Event.EventID"), nullable=False),
        sa.Column("UserID", sa.Integer(), sa.ForeignKey("dbo.Users.UserID"), nullable=True),
        sa.Column("LockedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("ClientIP", sa.String(length=45), nullable=True),
        sa.Column("UserAgent", sa.String(length=255), nullable=True),
        sa.Column("RequestID", sa.String(length=64), nullable=True),
        sa.Column("OldDate", sa.DateTime(), nullable=True),
        sa.Column("NewDate", sa.DateTime(), nullable=True),
        schema="dbo",
    )


def downgrade() -> None:
    try:
        op.drop_table("EventLockAudit", schema="dbo")
    except Exception:
        pass
