"""news 한국어 제목·요약 (2026-11-05) — 노트북 EXAONE 7.8B

- news_articles.title_ko · summary_ko · ko_model · ko_at · ko_tries(실패 횟수, 3번이면 더 시도 안 함)

Revision ID: 20261105_0003
Revises: 20261105_0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_0003"
down_revision: str | None = "20261105_0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("news_articles", sa.Column("title_ko", sa.String(500), nullable=True))
    op.add_column("news_articles", sa.Column("summary_ko", sa.Text(), nullable=True))
    op.add_column("news_articles", sa.Column("ko_model", sa.String(40), nullable=True))
    op.add_column("news_articles", sa.Column("ko_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "news_articles",
        sa.Column("ko_tries", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    for col in ("ko_tries", "ko_at", "ko_model", "summary_ko", "title_ko"):
        op.drop_column("news_articles", col)
