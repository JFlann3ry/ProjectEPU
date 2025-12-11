"""add rate limit counter table

Revision ID: 20251211_0027
Revises: 20250916_0026_add_remove_website_logo
Create Date: 2025-12-11 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251211_0027"
down_revision = "20250916_0026_add_remove_website_logo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "RateLimitCounter",
        sa.Column("Key", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("Window", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("Count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        schema="dbo",
    )


def downgrade() -> None:
    op.drop_table("RateLimitCounter", schema="dbo")