"""Add RemoveWebsiteLogo to EventCustomisation

Revision ID: 20250916_0026_add_remove_website_logo
Revises: 20250916_0025_add_email_change_requests
Create Date: 2025-09-16 17:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250916_0026_add_remove_website_logo'
down_revision = '20250916_0025_add_email_change_requests'
branch_labels = None
depends_on = None


def upgrade():
    # Add RemoveWebsiteLogo boolean column; default False
    with op.batch_alter_table('EventCustomisation', schema='dbo') as batch_op:
        batch_op.add_column(
            sa.Column('RemoveWebsiteLogo', sa.Boolean(), nullable=True, server_default=sa.text('0'))
        )


def downgrade():
    with op.batch_alter_table('EventCustomisation', schema='dbo') as batch_op:
        batch_op.drop_column('RemoveWebsiteLogo')
