"""add soft-flag columns to vision_uploads (Sentinel is_poster_warning 지속화)

Revision ID: 20260729_0001
Revises: 20260727_0001
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0001"
down_revision: str | None = "20260727_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vision_uploads",
        sa.Column("poster_confidence", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "vision_uploads",
        sa.Column("sharpness_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "vision_uploads",
        sa.Column("is_poster_warning", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("vision_uploads", "is_poster_warning")
    op.drop_column("vision_uploads", "sharpness_score")
    op.drop_column("vision_uploads", "poster_confidence")
