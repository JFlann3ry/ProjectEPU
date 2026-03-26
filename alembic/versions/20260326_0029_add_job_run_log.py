"""Add JobRunLog table for background job execution tracking."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260326_0029"
down_revision = "20260325_0028"
branch_labels = None
depends_on = None


def upgrade():
    """Create JobRunLog table."""
    op.create_table(
        "JobRunLog",
        sa.Column("JobRunLogID", sa.Integer(), nullable=False),
        sa.Column("JobName", sa.String(255), nullable=False),
        sa.Column("StepName", sa.String(255), nullable=True),
        sa.Column("StartedAt", sa.DateTime(), nullable=False),
        sa.Column("FinishedAt", sa.DateTime(), nullable=False),
        sa.Column("Succeeded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("Details", sa.Text(), nullable=True),
        sa.Column("CreatedAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("JobRunLogID"),
    )
    op.create_index("ix_JobRunLog_JobName", "JobRunLog", ["JobName"])
    op.create_index("ix_JobRunLog_StartedAt", "JobRunLog", ["StartedAt"])


def downgrade():
    """Drop JobRunLog table."""
    op.drop_index("ix_JobRunLog_StartedAt", "JobRunLog")
    op.drop_index("ix_JobRunLog_JobName", "JobRunLog")
    op.drop_table("JobRunLog")
