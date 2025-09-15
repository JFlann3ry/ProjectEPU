"""
Add AddonCatalog and EventAddonPurchase tables.

Revision ID: 20250908_0018
Revises: 20250908_0017
Create Date: 2025-09-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250908_0018"
down_revision = "20250908_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create AddonCatalog
    try:
        op.create_table(
            "AddonCatalog",
            sa.Column("AddonID", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("Code", sa.String(length=50), nullable=False, unique=True),
            sa.Column("Name", sa.String(length=120), nullable=False),
            sa.Column("Description", sa.Text(), nullable=True),
            sa.Column(
                "PriceCents", sa.Integer(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column(
                "Currency",
                sa.String(length=8),
                nullable=False,
                server_default=sa.text("'gbp'"),
            ),
            sa.Column(
                "AllowQuantity", sa.Boolean(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column(
                "MinQuantity", sa.Integer(), nullable=False, server_default=sa.text("1")
            ),
            sa.Column(
                "MaxQuantity", sa.Integer(), nullable=False, server_default=sa.text("1")
            ),
            sa.Column(
                "IsActive", sa.Boolean(), nullable=False, server_default=sa.text("1")
            ),
            sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
            schema="dbo",
        )
    except Exception:
        pass

    # Create EventAddonPurchase
    try:
        op.create_table(
            "EventAddonPurchase",
            sa.Column("PurchaseID", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "UserID",
                sa.Integer(),
                sa.ForeignKey("dbo.Users.UserID"),
                nullable=False,
            ),
            sa.Column(
                "EventID",
                sa.Integer(),
                sa.ForeignKey("Event.EventID"),
                nullable=True,
            ),
            sa.Column(
                "AddonID",
                sa.Integer(),
                sa.ForeignKey("dbo.AddonCatalog.AddonID"),
                nullable=False,
            ),
            sa.Column(
                "Quantity",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.Column("Amount", sa.Numeric(10, 2), nullable=False),
            sa.Column(
                "Currency",
                sa.String(length=8),
                nullable=False,
                server_default=sa.text("'GBP'"),
            ),
            sa.Column("StripeSessionID", sa.String(length=255), nullable=True),
            sa.Column("StripePaymentIntentID", sa.String(length=255), nullable=True),
            sa.Column(
                "Status",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
            schema="dbo",
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_table("EventAddonPurchase", schema="dbo")
    except Exception:
        pass
    try:
        op.drop_table("AddonCatalog", schema="dbo")
    except Exception:
        pass
