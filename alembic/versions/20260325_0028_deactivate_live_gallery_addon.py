"""Deactivate legacy live_gallery addon.

Revision ID: 20260325_0028
Revises: 20250913_0032_merge_heads, 20251211_0027
Create Date: 2026-03-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260325_0028"
down_revision = (
    "20250913_0032_merge_heads",
    "20251211_0027",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE dbo.AddonCatalog
            SET IsActive = 0
            WHERE LOWER(Code) = :code
            """
        ),
        {"code": "live_gallery"},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE dbo.AddonCatalog
            SET IsActive = 1
            WHERE LOWER(Code) = :code
            """
        ),
        {"code": "live_gallery"},
    )
