"""
Add CustomEventType table to record custom event type names per event.

Revision ID: 20250911_0020_add_custom_event_type
Revises: 20250910_add_plan_to_users
Create Date: 2025-09-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
# Short numeric revision id to avoid DB column truncation issues
revision = "20250911_0020_add_custom_event_type"
# previous migration file uses revision id '20250910_add_plan_to_users'
down_revision = "20250910_add_plan_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "CustomEventType",
        sa.Column(
            "CustomEventTypeID",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "EventID",
            sa.Integer(),
            sa.ForeignKey("Event.EventID"),
            nullable=False,
        ),
        sa.Column(
            "EventTypeID",
            sa.Integer(),
            sa.ForeignKey("dbo.EventType.EventTypeID"),
            nullable=True,
        ),
        sa.Column("CustomEventName", sa.String(length=255), nullable=True),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "UpdatedAt",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        schema="dbo",
    )


def downgrade() -> None:
    op.drop_table("CustomEventType", schema="dbo")
