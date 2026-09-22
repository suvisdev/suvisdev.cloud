"""gildle 산책 기록 테이블 (2026-09-22)

앱 출시를 gildle만 하기로 하면서 추가한다. 지금까지 gildle은 stateless 경로
계산기라 사용자가 다시 열 이유가 없었다 — 산책 기록이 그 상태를 만든다.

`user_id`에 FK를 걸지 않는다: `users`는 다른 앱의 테이블이고, gildle이 그것을
참조하면 앱 경계를 넘는 결합이 생긴다. 소유권 검사는 유스케이스가 한다.

Revision ID: 20260922_0001
Revises: 20260911_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260922_0001"
down_revision: str | None = "20260911_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "walks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=False),
        sa.Column("distance_m", sa.Integer(), nullable=False),
        sa.Column("duration_s", sa.Integer(), nullable=False),
        sa.Column("path", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("season_mode", sa.String(), nullable=False),
        sa.Column("avg_shade_score", sa.Float(), nullable=True),
        sa.Column("memo", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_walks_user_id", "walks", ["user_id"])
    # 기본 조회가 "내 최근 산책"이라 복합 인덱스로 정렬까지 받는다.
    op.create_index("ix_walks_user_started", "walks", ["user_id", sa.text("started_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_walks_user_started", table_name="walks")
    op.drop_index("ix_walks_user_id", table_name="walks")
    op.drop_table("walks")
