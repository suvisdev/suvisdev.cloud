"""add movies.origin_country JSONB column

TMDB `origin_country`(ISO 3166-1 alpha-2 **배열** — 공동제작이면 ['US','GB']처럼
여럿)를 저장한다. 같은 날 추가한 `original_language`만으로는 영어권(미국/영국/
호주)을 구분할 수 없어서 필요하다 — 한국·일본처럼 언어≈국가인 경우엔 두 컬럼의
판정이 일치하지만(표본 40편 불일치 0건), 영어권 질의는 언어로 갈라낼 수 없다.

배열이라 `platforms`(JSONB)와 같은 타입을 쓴다. nullable=True는 "TMDB가 빈
배열을 준 것"과 "아직 백필 안 됨"을 구분하기 위해서다(synopsis·original_language
와 동일 컨벤션) — 백필 순회가 `IS NULL`로 대상을 고른다.

Revision ID: 20260807_0002
Revises: 20260807_0001
Create Date: 2026-08-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260807_0002"
down_revision: str | None = "20260807_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("origin_country", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "origin_country")
