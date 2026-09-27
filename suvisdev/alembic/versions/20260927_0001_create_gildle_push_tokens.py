"""gildle FCM 토큰 테이블 (2026-09-27)

앱 푸시 알림용 기기 토큰. token이 유일키(같은 기기가 다른 계정으로 로그인하면
user_id 갱신). walks와 같은 이유로 users FK는 걸지 않는다.

Revision ID: 20260927_0001
Revises: 20260922_0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_0001"
down_revision: str | None = "20260922_0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "push_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_push_tokens_token"),
    )
    op.create_index("ix_push_tokens_user_id", "push_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_push_tokens_user_id", table_name="push_tokens")
    op.drop_table("push_tokens")
