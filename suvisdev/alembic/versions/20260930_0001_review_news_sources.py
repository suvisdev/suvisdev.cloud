"""reviews에 news_sources JSONB (2026-09-30 에디터 리뷰 출처 링크)

에디터 리뷰가 참고한 뉴스 기사 URL이 RSS에 있는데 생성 시 버려져, 신뢰도 배지(개수)만 있고
출처 링크는 못 보여줬다. 참고 기사 [{title, url, source}]를 저장해 링크로 표시한다. 유저 리뷰는
NULL, 백필 전 기존 에디터 리뷰도 NULL(개수 배지만 유지, 링크는 새 리뷰부터).

Revision ID: 20260930_0001
Revises: 20260929_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260930_0001"
down_revision: str | None = "20260929_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("reviews", sa.Column("news_sources", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("reviews", "news_sources")
