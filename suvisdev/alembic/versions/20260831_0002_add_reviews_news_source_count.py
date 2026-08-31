"""reviews.news_source_count 추가 — 에디터 리뷰 신뢰도 태그용.

Revision ID: 20260831_0002
Revises: 20260831_0001
"""

from __future__ import annotations

from alembic import op

revision: str = "20260831_0002"
down_revision: str | None = "20260831_0001"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS news_source_count INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS news_source_count")
