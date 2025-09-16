"""
Alembic migration script to add 'plan' and 'plan_purchase_date' columns to Users table.

Usage:
- Place this file in your alembic/versions/ directory.
- Edit the revision and down_revision as needed.
- Run: alembic upgrade head
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250910_add_plan_to_users'
down_revision = '20250908_0018'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        'Users',
        sa.Column(
            'plan',
            sa.String(length=32),
            nullable=False,
            server_default='free',
        ),
        schema='dbo',
    )
    op.add_column(
        'Users',
        sa.Column('plan_purchase_date', sa.DateTime(), nullable=True),
        schema='dbo',
    )

def downgrade():
    op.drop_column('Users', 'plan', schema='dbo')
    op.drop_column('Users', 'plan_purchase_date', schema='dbo')
