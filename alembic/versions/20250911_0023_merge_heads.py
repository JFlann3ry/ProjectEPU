"""merge heads 20250911_0021_add_eventtask and 20250911_0022_add_theme_isactive

Revision ID: 20250911_0023_merge_heads
Revises: 20250911_0021_add_eventtask, 20250911_0022_add_theme_isactive
Create Date: 2025-09-11 00:40:00.000000
"""

# revision identifiers, used by Alembic.
revision = '20250911_0023_merge_heads'
# Simplify merge to avoid referencing an ancestor+descendant pair which confuses Alembic.
# Originally listed ('20250911_0021_add_eventtask', '20250911_0022_add_theme_isactive')
# but 0022 is a descendant of 0021. Set the down_revision to the later head only.
down_revision = '20250911_0022_add_theme_isactive'
branch_labels = None
depends_on = None


def upgrade():
    # Merge-only revision; no DB operations needed.
    pass


def downgrade():
    pass
