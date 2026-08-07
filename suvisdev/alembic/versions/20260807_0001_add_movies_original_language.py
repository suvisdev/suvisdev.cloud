"""add movies.original_language TEXT column

TMDB `original_language`(ISO 639-1, 예: ko/en/th/ja)는 지금까지 import
경로 어디에도 저장되지 않았다 — 한국어/영어 외 언어 영화(태국어 등)를
카탈로그·추천에서 걸러낼 신호가 DB에 아예 없던 게 원인
(`_docs/WORK_LOG.md` 2026-08-07). age_rating(String(8))처럼 짧은 코드값이라
길이 상한을 두되, IETF 지역 서브태그(zh-CN 등) 여유를 감안해 String(8)로 둔다.

Revision ID: 20260807_0001
Revises: 20260806_0001
Create Date: 2026-08-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_0001"
down_revision: str | None = "20260806_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("original_language", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "original_language")
