import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250822_0008_add_theme_audit"
down_revision = "20250819_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ThemeAudit",
        sa.Column("AuditID", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ThemeID", sa.Integer, sa.ForeignKey("Theme.ThemeID"), nullable=False),
        sa.Column("UserID", sa.Integer, sa.ForeignKey("dbo.Users.UserID"), nullable=True),
        sa.Column("ChangedAt", sa.DateTime, server_default=sa.text("GETDATE()")),
        sa.Column("ClientIP", sa.String(45), nullable=True),
        sa.Column("UserAgent", sa.String(255), nullable=True),
        sa.Column("RequestID", sa.String(64), nullable=True),
        sa.Column("Changes", sa.String(4000), nullable=True),
        schema="dbo",
    )


def downgrade():
    op.drop_table("ThemeAudit", schema="dbo")
