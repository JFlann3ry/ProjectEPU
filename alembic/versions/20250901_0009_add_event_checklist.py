import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250901_0009"
down_revision = "20250822_0008_add_theme_audit"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "EventChecklist",
        sa.Column("EventChecklistID", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("EventID", sa.Integer, sa.ForeignKey("Event.EventID"), nullable=False),
        sa.Column("SharedOnce", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("CreatedAt", sa.DateTime, server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime, server_default=sa.func.now()),
        schema="dbo",
    )
    # Unique per event (optional but helpful)
    op.create_unique_constraint(
        "UQ_EventChecklist_EventID", "EventChecklist", ["EventID"], schema="dbo"
    )


def downgrade():
    try:
        op.drop_constraint("UQ_EventChecklist_EventID", "EventChecklist", schema="dbo")
    except Exception:
        pass
    op.drop_table("EventChecklist", schema="dbo")
