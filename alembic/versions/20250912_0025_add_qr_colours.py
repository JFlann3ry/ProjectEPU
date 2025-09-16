"""Add QRFillColour and QRBackColour to EventCustomisation

Revision ID: 20250912_0025_add_qr_colours
Revises: 20250912_0024_final_merge
Create Date: 2025-09-12 00:25:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250912_0025_add_qr_colours'
down_revision = '20250912_0024_final_merge'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('EventCustomisation', schema='dbo') as batch_op:
        batch_op.add_column(sa.Column('QRFillColour', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('QRBackColour', sa.String(length=16), nullable=True))


def downgrade():
    with op.batch_alter_table('EventCustomisation', schema='dbo') as batch_op:
        batch_op.drop_column('QRBackColour')
        batch_op.drop_column('QRFillColour')
