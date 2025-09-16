"""Add EmailChangeRequests table

Revision ID: 20250916_0025_add_email_change_requests
Revises: 20250913_0032_merge_heads_gallery_order
Create Date: 2025-09-16
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250916_0025_add_email_change_requests"
down_revision = "20250913_0032_merge_heads_gallery_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "EmailChangeRequests",
        sa.Column("ID", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("UserID", sa.Integer, sa.ForeignKey("dbo.Users.UserID"), nullable=False),
        sa.Column("OldEmail", sa.String(255), nullable=False),
        sa.Column("NewEmail", sa.String(255), nullable=False),
        sa.Column("Token", sa.String(512), nullable=False, unique=True),
        sa.Column("CreatedAt", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("ExpiresAt", sa.DateTime, nullable=True),
        sa.Column("CompletedAt", sa.DateTime, nullable=True),
        sa.Column("ReversedAt", sa.DateTime, nullable=True),
        sa.Column("IsActive", sa.Boolean, nullable=False, server_default=sa.text("1")),
        schema="dbo",
    )


def downgrade() -> None:
    op.drop_table("EmailChangeRequests", schema="dbo")
