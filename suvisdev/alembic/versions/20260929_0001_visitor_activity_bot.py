"""visitor_activity에 is_bot·user_agent (2026-09-29 방문자 봇 구분)

09-28 방문 22명 중 19명이 새 쿠키·0초 체류였는데 사람·봇을 가를 정보가 없었다. 첫 핑의 User-Agent로
봇을 판정해 통계에서 나눈다. 기존 행은 is_bot=false(사람으로 간주), user_agent NULL.

Revision ID: 20260929_0001
Revises: 20260927_0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260929_0001"
down_revision: str | None = "20260927_0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "visitor_activity",
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("visitor_activity", sa.Column("user_agent", sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column("visitor_activity", "user_agent")
    op.drop_column("visitor_activity", "is_bot")
