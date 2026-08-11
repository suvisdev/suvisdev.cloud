"""add HNSW indexes on movies.embedding and hub_knowledge.embedding

벡터 인덱스가 저장소 전체에 0건이라 유사도 쿼리가 seq scan으로 돈다.
`movies.embedding`(2014행)·`hub_knowledge.embedding`(2014행) 둘 다 cosine 거리
기반 검색이므로 `vector_cosine_ops` opclass로 HNSW 인덱스를 만든다.

파라미터 m=16 / ef_construction=64 는 pgvector 기본값. 지금 규모(2014행)에서
빌드 몇 초, 후속 리뷰 임베딩 추가로 자릿수가 늘어나도 안정적.

CONCURRENTLY는 alembic 트랜잭션과 충돌하므로 쓰지 않는다. 지금 규모는 잠깐의
락으로 충분해 다운타임을 무시할 수 있다.

Revision ID: 20260811_0001
Revises: 20260810_0001
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260811_0001"
down_revision: str | None = "20260810_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_movies_embedding_hnsw
        ON movies USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_hub_knowledge_embedding_hnsw
        ON hub_knowledge USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_hub_knowledge_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_movies_embedding_hnsw")
