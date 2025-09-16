"""Normalize plan revision references and merge tiny inconsistency

Revision ID: 20250912_0021_merge_plan_revision
Revises: add_plan_to_users, 20250911_0021_add_eventtask
Create Date: 2025-09-12
"""
# alembic.op import removed: this merge-only revision performs no DB ops

# revision identifiers, used by Alembic.
revision = "20250912_0021_merge_plan_revision"
# Avoid ancestor+descendant tuple: use the later head only.
down_revision = "20250911_0021_add_eventtask"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision to reconcile non-uniform revision ids; no DB ops.
    pass


def downgrade() -> None:
    pass
