"""hub_knowledge.embedding 768→1024 — RAG 임베딩 bge-m3 전환(2026-09-11).

eval_embedding_models.py 실측: 한국어 검색에서 현행 nomic-embed-text
recall@8=0.390 vs bge-m3 0.860. bge-m3는 1024차원이라 컬럼 확장이 필요하다.
차원이 다른 기존 벡터는 재사용 불가라 NULL로 비운다 — 적용 직후
`scripts/ingest_hub_knowledge.py --reset`으로 재임베딩할 것(절차:
suvisdev/_docs/RS_TEACHER_LOOP.md §임베딩 컷오버).

movies/reviews/taste_vectors(768, Gemini 계열)와 dispatch(768, 자체 상수)는
별개 공간이라 건드리지 않는다.

Revision ID: 20260911_0001
Revises: 20260901_0001
"""

from __future__ import annotations

from alembic import op

revision: str = "20260911_0001"
down_revision: str | None = "20260901_0001"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE hub_knowledge ALTER COLUMN embedding TYPE vector(1024) USING NULL")


def downgrade() -> None:
    # 1024 벡터도 768로 되돌릴 수 없어 NULL — 다운그레이드 후에도 재임베딩 필요.
    op.execute("ALTER TABLE hub_knowledge ALTER COLUMN embedding TYPE vector(768) USING NULL")
