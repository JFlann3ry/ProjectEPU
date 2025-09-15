"""add Theme.IsActive column

Revision ID: 20250911_0022_add_theme_isactive
Revises: 20250911_0021_add_eventtask
Create Date: 2025-09-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250911_0022_add_theme_isactive'
# Make this revision a sibling of 20250911_0021 so the merge revision properly merges two branches.
down_revision = '20250911_0021_add_eventtask'
branch_labels = None
depends_on = None


def upgrade():
    # Add IsActive boolean with default True for existing rows
    op.add_column('Theme', sa.Column('IsActive', sa.Boolean(), nullable=False, server_default=sa.text('1')))


def downgrade():
    op.drop_column('Theme', 'IsActive')
