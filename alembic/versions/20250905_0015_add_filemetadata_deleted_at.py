"""Compatibility stub: superseded by 20250905_0015a_add_filemetadata_deleted_at.

This module is a no-op and is chained AFTER the real migration to avoid
creating multiple heads on systems where both filenames exist.
"""

# No-op; real migration is in 20250905_0015a_add_filemetadata_deleted_at.py
revision = '20250905_0015'
# Chain this no-op after the actual migration to avoid multiple heads
down_revision = '20250905_0015a'
branch_labels = None
depends_on = None

def upgrade():
    pass


def downgrade():
    pass
