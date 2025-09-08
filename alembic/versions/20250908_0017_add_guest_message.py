"""
Add GuestMessage table (guestbook messages).

Revision ID: 20250908_0017
Revises: 20250905_0016
Create Date: 2025-09-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250908_0017"
down_revision = "20250905_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create GuestMessage if it doesn't exist
    try:
        op.create_table(
            "GuestMessage",
            sa.Column("GuestMessageID", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("EventID", sa.Integer(), sa.ForeignKey("dbo.Event.EventID"), nullable=False),
            sa.Column(
                "GuestSessionID",
                sa.Integer(),
                sa.ForeignKey("dbo.GuestSession.GuestID"),
                nullable=True,
            ),
            sa.Column("DisplayName", sa.String(length=80), nullable=True),
            sa.Column("Message", sa.String(length=300), nullable=False),
            sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("Deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            schema="dbo",
        )
    except Exception:
        # Table may already exist
        pass


def downgrade() -> None:
    try:
        op.drop_table("GuestMessage", schema="dbo")
    except Exception:
        pass
