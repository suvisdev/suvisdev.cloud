"""create pdf_loader_documents table (silicon_valley PDF 업로드→추출→요약 파이프라인)

Revision ID: 20260727_0001
Revises: f3a7c9e21b6d
Create Date: 2026-07-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0001"
down_revision: str | None = "f3a7c9e21b6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pdf_loader_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("pdf_loader_documents")
