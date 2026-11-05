"""news 섹션·출처 묶음 (2026-11-05) — 메인 AI 기술 + 부록 경제

- news_articles.section (ai | economy), news_articles.feed_group (연구소 블로그·논문·릴리스·… / 경제 언론 / 검색)
- news_topics.section — 검색어 탭이 어느 섹션 기사에서 찾는지
- ix_news_articles_section_sort_at — 섹션별 최신 목록

Revision ID: 20261105_0002
Revises: 20261105_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_0002"
down_revision: str | None = "20261105_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "news_articles",
        sa.Column("section", sa.String(16), nullable=False, server_default="ai"),
    )
    op.add_column(
        "news_articles",
        sa.Column("feed_group", sa.String(16), nullable=False, server_default=""),
    )
    op.create_index("ix_news_articles_section_sort_at", "news_articles", ["section", "sort_at"])
    op.add_column(
        "news_topics",
        sa.Column("section", sa.String(16), nullable=False, server_default="ai"),
    )


def downgrade() -> None:
    op.drop_column("news_topics", "section")
    op.drop_index("ix_news_articles_section_sort_at", table_name="news_articles")
    op.drop_column("news_articles", "feed_group")
    op.drop_column("news_articles", "section")
