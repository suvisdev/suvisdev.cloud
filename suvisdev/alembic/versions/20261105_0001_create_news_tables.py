"""news.suvisdev.cloud 수집 테이블 4개 (2026-11-05, apps/news 1단계)

- news_topics: 운영자가 저장한 검색어 = 화면 탭
- news_articles: 수집 기사(검색 API·RSS). 본문은 RSS 가 직접 준 것만, 원문 페이지는 가져오지 않는다
- news_topic_articles: 탭 ↔ 기사 + 관련성 점수
- news_verdicts: AI 판정(층마다 1건 — rules / llm). 배지는 숨기지 않고 표시용

Revision ID: 20261105_0001
Revises: 20261028_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261105_0001"
down_revision: str | None = "20261028_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "news_topics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("query", sa.String(100), nullable=False, unique=True),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("canonical_url", sa.String(1000), nullable=False, unique=True),
        sa.Column("link", sa.String(1000), nullable=True),
        sa.Column("source_domain", sa.String(200), nullable=False),
        sa.Column("source_name", sa.String(100), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("author", sa.String(100), nullable=False, server_default=""),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_news_articles_source_domain", "news_articles", ["source_domain"])
    op.create_index("ix_news_articles_sort_at", "news_articles", ["sort_at"])
    op.create_index("ix_news_articles_origin_sort_at", "news_articles", ["origin", "sort_at"])
    op.create_table(
        "news_topic_articles",
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("news_topics.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("news_articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("relevance", sa.Float(), nullable=False),
        sa.Column(
            "matched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_news_topic_articles_article_id", "news_topic_articles", ["article_id"])
    op.create_table(
        "news_verdicts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("news_articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layer", sa.String(16), nullable=False),
        sa.Column("harness_version", sa.String(16), nullable=False),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("badge", sa.String(16), nullable=False),
        sa.Column("reasons_ko", postgresql.JSONB(), nullable=False),
        sa.Column("signals", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("article_id", "layer", name="uq_news_verdicts_article_layer"),
    )


def downgrade() -> None:
    op.drop_table("news_verdicts")
    op.drop_index("ix_news_topic_articles_article_id", table_name="news_topic_articles")
    op.drop_table("news_topic_articles")
    op.drop_index("ix_news_articles_origin_sort_at", table_name="news_articles")
    op.drop_index("ix_news_articles_sort_at", table_name="news_articles")
    op.drop_index("ix_news_articles_source_domain", table_name="news_articles")
    op.drop_table("news_articles")
    op.drop_table("news_topics")
