"""add movies.synopsis TEXT column

TMDB `overview`는 import 시점에 이미 파싱되지만(`tmdb_mapper.py::map_tmdb_row`)
hub_knowledge 텍스트에만 쓰이고 movies 테이블에는 저장되지 않았다 — 상세
화면 synopsis가 항상 빈 문자열이던 원인(`_docs/MOVA_UI_QUICK_WINS.md` §2).
title/poster_url과 같은 서사형 텍스트 컬럼이라 길이 상한 없는 TEXT를 쓴다
(character_name TEXT 마이그레이션 20260805_0001과 동일 컨벤션).

Revision ID: 20260806_0001
Revises: 20260805_0001
Create Date: 2026-08-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0001"
down_revision: str | None = "20260805_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("synopsis", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "synopsis")
