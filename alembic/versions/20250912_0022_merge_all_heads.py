"""Final merge of all current heads into a single head.

Revision ID: 20250912_0022_merge_all_heads
Revises: 20250912_0020_merge_heads, 20250912_0021_merge_plan_revision
Create Date: 2025-09-12
"""

# revision identifiers, used by Alembic.
revision = "20250912_0022_merge_all_heads"
# Avoid ancestor+descendant tuple; depend on the later head only.
down_revision = "20250912_0020_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; no DB operations required.
    pass


def downgrade() -> None:
    pass
