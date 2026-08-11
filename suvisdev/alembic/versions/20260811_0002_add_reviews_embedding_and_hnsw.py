"""add reviews.embedding vector(768) + HNSW index

사용자 취향 벡터의 원천이 되는 리뷰 본문 임베딩. mova 추천에서 유저별
개인화 신호로 쓸 것이라 movies·hub_knowledge와 같은 차원(768)·같은
opclass(cosine)로 정렬해 취향-영화 매칭이 그대로 성립하게 한다.

컬럼 자체는 `pgvector.sqlalchemy.Vector(768)`이지만 alembic op에서는
raw SQL로 다룬다(ORM 반영과 별개, MovaReview에 컬럼 추가는 같은
사이클에서 함께).

HNSW는 20260811_0001과 같은 파라미터(m=16, ef_construction=64)로. 지금
행이 3건뿐이라 인덱스가 planner 자동 선택되지는 않을 것이나(pgvector
cost 오판, 0.5순위 사이클 확인), 리뷰가 늘어나면 자연 반영되고 필요
시엔 `find_similar_movies`처럼 세션 힌트를 붙이면 된다.

Revision ID: 20260811_0002
Revises: 20260811_0001
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260811_0002"
down_revision: str | None = "20260811_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE reviews ADD COLUMN embedding vector(768)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reviews_embedding_hnsw
        ON reviews USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_reviews_embedding_hnsw")
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS embedding")
