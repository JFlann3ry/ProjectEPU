"""add DeletedAt to FileMetadata

Revision ID: 20250905_0015a
Revises: 20250903_0014
Create Date: 2025-09-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250905_0015a'
down_revision = '20250903_0014'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('FileMetadata', sa.Column('DeletedAt', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('FileMetadata', 'DeletedAt')
