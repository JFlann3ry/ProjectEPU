"""Merge multiple alembic heads into a single head

Revision ID: 20250912_0030_merge_heads_fix
Revises: 20250912_0021_merge_plan_revision, 20250912_0023_merge_11, 20250912_0025_add_qr_colours
Create Date: 2025-09-12 12:35:00.000000
"""

# revision identifiers, used by Alembic.
revision = '20250912_0030_merge_heads_fix'
down_revision = (
    '20250912_0021_merge_plan_revision',
    '20250912_0023_merge_11',
    '20250912_0025_add_qr_colours',
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a no-op migration that exists solely to join multiple heads
    # into a single head so that `alembic upgrade head` and other commands
    # behave predictably. No schema changes are performed here.
    pass


def downgrade() -> None:
    # No-op downgrade for the merge migration.
    pass
