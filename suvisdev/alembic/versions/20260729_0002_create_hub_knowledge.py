"""create hub_knowledge table (ontology Hub RAG 지식 저장소)

HubKnowledgeOrm(apps/ontology/adapter/outbound/orm/hub_knowledge_orm.py)은
2026-07-14(cc2c334)에 추가됐지만 이 리비전 전까지 마이그레이션 체인에
CREATE가 없었다 — ensure_titanic_tables()의 create_all()로만 생성되어
빈 DB에서 alembic upgrade head만으로는 hub_knowledge가 만들어지지 않았다.

Revision ID: 20260729_0002
Revises: 20260729_0001
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260729_0002"
down_revision: str | None = "20260729_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "hub_knowledge",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("embedding", Vector(_EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_ref"),
    )
    op.create_index("ix_hub_knowledge_source", "hub_knowledge", ["source"])
    op.create_index("ix_hub_knowledge_source_ref", "hub_knowledge", ["source_ref"])


def downgrade() -> None:
    op.drop_index("ix_hub_knowledge_source_ref", table_name="hub_knowledge")
    op.drop_index("ix_hub_knowledge_source", table_name="hub_knowledge")
    op.drop_table("hub_knowledge")
