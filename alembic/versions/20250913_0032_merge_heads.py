"""Merge current alembic heads into a single head

Revision ID: 20250913_0032_merge_heads
Revises: 20250912_0030_merge_heads_fix, 20250913_0031_add_event_gallery_order
Create Date: 2025-09-13
"""

# revision identifiers, used by Alembic.
revision = "20250913_0032_merge_heads"
down_revision = (
    "20250912_0030_merge_heads_fix",
    "20250913_0031_add_event_gallery_order",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op merge revision to unify heads so `alembic upgrade head` works.
    pass


def downgrade() -> None:
    pass
