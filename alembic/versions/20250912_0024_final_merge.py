"""Final merge to unify all heads

Revision ID: 20250912_0024_final_merge
Revises: 20250912_0022_merge_all_heads, 20250912_0023_merge_11
Create Date: 2025-09-12
"""

# revision identifiers, used by Alembic.
revision = "20250912_0024_final_merge"
# Depend on the canonical merged head only to avoid ancestor/descendant overlap.
down_revision = "20250912_0022_merge_all_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision to unify heads
    pass


def downgrade() -> None:
    pass
