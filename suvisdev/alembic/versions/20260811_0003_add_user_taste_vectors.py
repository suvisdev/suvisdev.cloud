"""add user_taste_vectors table (mova)

유저 취향 벡터 = 본인 리뷰 임베딩의 별점 가중 평균. mova 추천 개인화 신호.
컬럼을 users(viewer 소유)에 붙이지 않고 mova 신규 테이블로 분리하는 이유는
스타-토폴로지(Spoke-Spoke 경계) 유지 — mova 도메인 값이라 mova에 산다.
FK는 동일 DB라 `viewer.users.id`를 그대로 참조한다(cross-metadata FK, mova
전례 그대로).

HNSW 인덱스는 이번엔 안 만든다 — 조회가 `WHERE user_id = ?` 단건뿐이라
인덱스가 무의미하다. 다음 사이클(추천 반영)에서 유사 유저 탐색이 도입되면
별도 리비전으로 추가.

Revision ID: 20260811_0003
Revises: 20260811_0002
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260811_0003"
down_revision: str | None = "20260811_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_taste_vectors (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            vector vector(768),
            review_count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_user_taste_vectors_user_id UNIQUE (user_id)
        )
        """
    )
    op.execute("CREATE INDEX ix_user_taste_vectors_user_id ON user_taste_vectors (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_taste_vectors")
