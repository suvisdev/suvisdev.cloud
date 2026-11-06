"""news 오늘의 핫한 소식 칸 + 내용 없는 글의 지어낸 요약 지우기 (2026-11-06)

- news_articles.hot_source · hot_score · hot_label · hot_at + ix_news_articles_hot
- 데이터: Hacker News·Reddit 링크 글은 요약 칸이 "Article URL … Points …", "submitted by /u/… [link] [comments]" 뿐이라
  모델이 제목만 보고 지어냈다('LLM Voice' → "LLM 의 음성 표현 기술"). 껍데기를 걷어 내고, 남는 내용이 없으면 한국어 요약을 지워
  다음 주기에 제목만 다시 옮기게 한다. 내용이 있는 글의 요약은 건드리지 않는다.

Revision ID: 20261105_0004
Revises: 20261105_0003
"""

from __future__ import annotations

import re

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_0004"
down_revision: str | None = "20261105_0003"
branch_labels: str | None = None
depends_on: str | None = None

_MIN_SOURCE_CHARS = (
    40  # domain/feed_text.py MIN_SOURCE_CHARS — 마이그레이션은 앱 코드에 기대지 않는다
)
_HN_META = re.compile(
    r"(?:Article URL:\s*\S*|Comments URL:\s*\S*|Points:\s*\d+|#\s*Comments:\s*\d+)", re.IGNORECASE
)
_REDDIT = re.compile(
    r"submitted\s+by\s+/?u/\S+(?:\s*\[link\])?(?:\s*\[comments\])?\s*$", re.IGNORECASE
)
_BARE = re.compile(r"\[(?:link|comments)\]", re.IGNORECASE)


def _clean(text: str) -> str:
    return " ".join(_BARE.sub(" ", _REDDIT.sub(" ", _HN_META.sub(" ", text))).split())


def upgrade() -> None:
    op.add_column("news_articles", sa.Column("hot_source", sa.String(8), nullable=True))
    op.add_column("news_articles", sa.Column("hot_score", sa.Integer(), nullable=True))
    op.add_column("news_articles", sa.Column("hot_label", sa.String(60), nullable=True))
    op.add_column("news_articles", sa.Column("hot_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_news_articles_hot", "news_articles", ["hot_source", "hot_score"])

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, summary, body FROM news_articles "
            "WHERE summary LIKE '%Article URL:%' OR summary LIKE '%submitted by%' OR summary LIKE '%Points:%'"
        )
    ).all()
    for row_id, summary, body in rows:
        cleaned = _clean(summary or "")
        empty = len(cleaned) + len(_clean(body or "")) < _MIN_SOURCE_CHARS
        if empty:
            conn.execute(
                sa.text(
                    "UPDATE news_articles SET summary = :s, summary_ko = NULL, title_ko = NULL, "
                    "ko_model = NULL, ko_at = NULL, ko_tries = 0 WHERE id = :i"
                ),
                {"s": cleaned, "i": row_id},
            )
        else:
            conn.execute(
                sa.text("UPDATE news_articles SET summary = :s WHERE id = :i"),
                {"s": cleaned, "i": row_id},
            )


def downgrade() -> None:
    # 데이터 정리는 되돌리지 않는다(지어낸 요약을 복원할 이유가 없다)
    op.drop_index("ix_news_articles_hot", table_name="news_articles")
    for col in ("hot_at", "hot_label", "hot_score", "hot_source"):
        op.drop_column("news_articles", col)
