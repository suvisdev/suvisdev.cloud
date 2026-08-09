"""add movies.trailer_key TEXT column

TMDB `videos`(append_to_response) 중 YouTube Trailer의 video key만 저장한다
(예: "LEEtpP6dkIY" — 풀 URL이 아니라 `https://www.youtube.com/embed/{key}`
조립에 쓰는 식별자). nullable=True는 synopsis·origin_country와 같은 컨벤션 —
"TMDB에 트레일러가 없음"과 "아직 백필 안 됨"을 구분하지 않는다(스칼라 컬럼이라
빈 문자열 sentinel도 마땅치 않아 origin_country류와 달리 이 구분 자체를 포기함,
상세: scripts/backfill_trailer_cli.py의 재조회 한계 주석).

Revision ID: 20260809_0001
Revises: 20260807_0002
Create Date: 2026-08-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0001"
down_revision: str | None = "20260807_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("trailer_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "trailer_key")
