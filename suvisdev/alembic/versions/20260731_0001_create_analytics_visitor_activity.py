"""create visitor_activity table (analytics 앱 — 자체 방문자 집계)

어드민 통계 방문자 탭(지금 접속/오늘/최근 7일/누적)을 위해 익명 방문자를
쿠키 UUID로 식별해 하루 1행으로 기록한다. visitor_id에는 PII가 없다.

Revision ID: 20260731_0001
Revises: 20260730_0001
Create Date: 2026-07-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0001"
down_revision: str | None = "20260730_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "visitor_activity",
        sa.Column("visitor_id", sa.String(), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("visitor_id", "visit_date"),
    )
    op.create_index(
        "ix_visitor_activity_last_seen_at", "visitor_activity", ["last_seen_at"]
    )
    op.create_index("ix_visitor_activity_visit_date", "visitor_activity", ["visit_date"])


def downgrade() -> None:
    op.drop_index("ix_visitor_activity_visit_date", table_name="visitor_activity")
    op.drop_index("ix_visitor_activity_last_seen_at", table_name="visitor_activity")
    op.drop_table("visitor_activity")
