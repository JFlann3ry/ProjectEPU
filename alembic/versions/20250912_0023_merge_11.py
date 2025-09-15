"""Merge 20250911_0020 and 20250911_0022 to resolve overlap

Revision ID: 20250912_0023_merge_11
Revises: 20250911_0021_add_eventtask, 20250911_0022_add_theme_isactive
Create Date: 2025-09-12
"""

# revision identifiers, used by Alembic.
revision = "20250912_0023_merge_11"
# Avoid referencing an ancestor+descendant pair; make this merge depend only on the later head.
down_revision = "20250911_0022_add_theme_isactive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision to reconcile overlapping requested revisions
    pass


def downgrade() -> None:
    pass
