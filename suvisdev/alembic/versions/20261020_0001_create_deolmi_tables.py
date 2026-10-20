"""덜미(매크로 탐지) 테이블 (2026-10-20)

deolmi_sites: 고객별 공개 키 + 비밀 키 해시·허용 도메인.
deolmi_events: /score 한 번에 한 줄(행동 수치·판정) — 모델 재학습 원천.

Revision ID: 20261020_0001
Revises: 20261007_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0001"
down_revision: str | None = "20261007_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "deolmi_sites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_key", sa.String(), nullable=False),
        sa.Column("secret_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), server_default="starter", nullable=False),
        sa.Column("domains", sa.String(), server_default="", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_key", name="uq_deolmi_sites_site_key"),
    )
    op.create_table(
        "deolmi_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("ip", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("rule_score", sa.Float(), nullable=False),
        sa.Column("model_score", sa.Float(), nullable=True),
        sa.Column("decided_by", sa.String(), nullable=False),
        sa.Column("signals", postgresql.JSONB(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["deolmi_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deolmi_events_site_id_created_at", "deolmi_events", ["site_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_deolmi_events_site_id_created_at", table_name="deolmi_events")
    op.drop_table("deolmi_events")
    op.drop_table("deolmi_sites")
