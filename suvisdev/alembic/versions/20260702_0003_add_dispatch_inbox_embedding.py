"""add embedding column (pgvector) to dispatch_inbox

Revision ID: 20260702_0003
Revises: 20260701_0002
Create Date: 2026-07-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260702_0003"
down_revision: str | None = "20260701_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# nomic-embed-text embedding_length (Ollama GET /api/tags 로 확인, 2026-07-02).
# 이후 임베딩 모델이 바뀌어도 과거 마이그레이션 기록은 당시 값으로 고정한다.
_EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "dispatch_inbox",
        sa.Column("embedding", Vector(_EMBEDDING_DIM), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dispatch_inbox", "embedding")
