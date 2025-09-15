"""Add EventGalleryOrder table

Revision ID: 20250913_0031_add_event_gallery_order
Revises: 20250912_0024_final_merge
Create Date: 2025-09-13
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250913_0031_add_event_gallery_order"
down_revision = "20250912_0024_final_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "EventGalleryOrder",
        sa.Column("EventGalleryOrderID", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("EventID", sa.Integer(), nullable=False),
        sa.Column("FileMetadataID", sa.Integer(), nullable=False),
        sa.Column("Ordinal", sa.Integer(), nullable=False),
        sa.Column("UpdatedAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    # Add foreign key constraints to ensure referential integrity
    op.create_foreign_key("fk_eventgalleryorder_event", "EventGalleryOrder", "Event", ["EventID"], ["EventID"])
    op.create_foreign_key(
        "fk_eventgalleryorder_filemetadata",
        "EventGalleryOrder",
        "FileMetadata",
        ["FileMetadataID"],
        ["FileMetadataID"],
    )

    op.create_unique_constraint("uq_event_ordinal", "EventGalleryOrder", ["EventID", "Ordinal"])
    op.create_unique_constraint("uq_event_file", "EventGalleryOrder", ["EventID", "FileMetadataID"])
    op.create_index("ix_event_gallery_order_event_file", "EventGalleryOrder", ["EventID", "FileMetadataID"])


def downgrade() -> None:
    # Drop objects in reverse order of creation to avoid dependency issues
    op.drop_index("ix_event_gallery_order_event_file", table_name="EventGalleryOrder")
    op.drop_constraint("uq_event_file", "EventGalleryOrder", type_="unique")
    op.drop_constraint("uq_event_ordinal", "EventGalleryOrder", type_="unique")
    # Drop foreign keys before dropping the table
    op.drop_constraint("fk_eventgalleryorder_filemetadata", "EventGalleryOrder", type_="foreignkey")
    op.drop_constraint("fk_eventgalleryorder_event", "EventGalleryOrder", type_="foreignkey")
    op.drop_table("EventGalleryOrder")
