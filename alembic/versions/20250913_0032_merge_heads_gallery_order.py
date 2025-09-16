"""Merge heads for gallery order

Revision ID: 20250913_0032_merge_heads_gallery_order
Revises: 20250912_0030_merge_heads_fix, 20250913_0031_add_event_gallery_order
Create Date: 2025-09-13
"""

# revision identifiers, used by Alembic.
revision = "20250913_0032_merge_heads_gallery_order"
down_revision = (
    "20250912_0030_merge_heads_fix",
    "20250913_0031_add_event_gallery_order",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a no-op merge revision to unify diverging heads so that
    # `alembic upgrade head` can be used. No schema changes here.
    pass


def downgrade() -> None:
    # No-op downgrade for merge migration.
    pass
