import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250901_0012"
down_revision = "20250901_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "UserDataExportJob",
        sa.Column("JobID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("UserID", sa.Integer(), nullable=False),
        sa.Column("Status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("CreatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("CompletedAt", sa.DateTime(), nullable=True),
        sa.Column("ExpiresAt", sa.DateTime(), nullable=True),
        sa.Column("FilePath", sa.String(length=500), nullable=True),
        sa.Column("ErrorMessage", sa.Text(), nullable=True),
        schema="dbo",
    )
    # FK to Users
    op.create_foreign_key(
        "FK_UserDataExportJob_User",
        "UserDataExportJob",
        "Users",
        ["UserID"],
        ["UserID"],
        source_schema="dbo",
        referent_schema="dbo",
    )


def downgrade():
    op.drop_constraint(
        "FK_UserDataExportJob_User", "UserDataExportJob", type_="foreignkey", schema="dbo"
    )
    op.drop_table("UserDataExportJob", schema="dbo")
