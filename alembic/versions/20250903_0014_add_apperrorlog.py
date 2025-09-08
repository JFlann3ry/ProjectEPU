"""create AppErrorLog table

Revision ID: 20250903_0014
Revises: 20250903_0013
Create Date: 2025-09-03 01:14:00
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250903_0014"
down_revision = "20250903_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "AppErrorLog",
        sa.Column("ErrorID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("OccurredAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("RequestID", sa.String(length=64), nullable=True),
        sa.Column("Path", sa.String(length=500), nullable=True),
        sa.Column("Method", sa.String(length=16), nullable=True),
        sa.Column("StatusCode", sa.Integer(), nullable=True),
        sa.Column("UserID", sa.Integer(), nullable=True),
        sa.Column("ClientIP", sa.String(length=45), nullable=True),
        sa.Column("UserAgent", sa.String(length=255), nullable=True),
        sa.Column("Referer", sa.String(length=500), nullable=True),
        sa.Column("Message", sa.Text(), nullable=True),
        sa.Column("StackTrace", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_AppErrorLog_OccurredAt",
        "AppErrorLog",
        ["OccurredAt"],
        unique=False,
    )
    op.create_index(
        "ix_AppErrorLog_RequestID",
        "AppErrorLog",
        ["RequestID"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_AppErrorLog_RequestID", table_name="AppErrorLog")
    op.drop_index("ix_AppErrorLog_OccurredAt", table_name="AppErrorLog")
    op.drop_table("AppErrorLog")
