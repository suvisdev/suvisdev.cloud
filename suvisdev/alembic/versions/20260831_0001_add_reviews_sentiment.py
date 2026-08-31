"""add reviews.sentiment_label, sentiment_score columns (mova)

Echo 감정분석(EXAONE LoRA) 결과를 리뷰에 저장. 로컬 GPU 배치에서 채우고,
EC2에서는 결과만 읽는다. body가 없으면 둘 다 NULL.

Revision ID: 20260831_0001
Revises: 20260825_0001
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260831_0001"
down_revision: str | None = "20260825_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE reviews ADD COLUMN sentiment_label TEXT")
    op.execute("ALTER TABLE reviews ADD COLUMN sentiment_score DOUBLE PRECISION")


def downgrade() -> None:
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS sentiment_score")
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS sentiment_label")
