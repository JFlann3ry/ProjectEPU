"""add composite index on FileMetadata (EventID, CapturedDateTime)

Revision ID: 20250903_0013
Revises: 20250901_0012
Create Date: 2025-09-03 00:13:00
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20250903_0013'
down_revision = '20250901_0012'
branch_labels = None
depends_on = None


def upgrade():
    # Use naming convention or explicit name depending on your metadata
    op.create_index(
        'ix_FileMetadata_EventID_CapturedDateTime',
        'FileMetadata',
        ['EventID', 'CapturedDateTime'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_FileMetadata_EventID_CapturedDateTime', table_name='FileMetadata')
