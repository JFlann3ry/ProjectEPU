"""
Merge heads: reconcile existing branch and new albums migration.

Revision ID: 20250912_0020_merge_heads
Revises: 20250911_0023_merge_heads, 20250912_0019
Create Date: 2025-09-12
"""

from __future__ import annotations


# revision identifiers, used by Alembic.
revision = "20250912_0020_merge_heads"
# Avoid ancestor+descendant tuple: 20250911_0023_merge_heads is ancestor of 20250912_0019
# Use the later head only.
down_revision = "20250912_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; no DB operations required.
    pass


def downgrade() -> None:
    pass
