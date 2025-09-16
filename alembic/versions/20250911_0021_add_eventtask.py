"""Add EventTask table

Revision ID: 20250911_0021_add_eventtask
Revises: 20250911_0020_add_custom_event_type
Create Date: 2025-09-11 00:21:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250911_0021_add_eventtask'
down_revision = '20250911_0020_add_custom_event_type'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'EventTask',
        sa.Column('EventTaskID', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('EventID', sa.Integer(), nullable=False),
        sa.Column('UserID', sa.Integer(), nullable=False),
        sa.Column('Key', sa.String(length=64), nullable=False),
        sa.Column('State', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('CompletedAt', sa.DateTime(), nullable=True),
        sa.Column('CreatedAt', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('UpdatedAt', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    # Add FK constraints if using schema-qualified tables; keep simple here


def downgrade():
    op.drop_table('EventTask')
