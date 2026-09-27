"""gildle route_requests·route_results 삭제 (2026-09-27 데드 코드 정리)

2026-07-28 생성 후 한 번도 쓰이지 않았다(0행, 어떤 유스케이스도 참조 안 함). "최근 계산 경로"
기능은 필요해지면 그때 새로 설계한다.

Revision ID: 20260927_0002
Revises: 20260927_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_0002"
down_revision: str | None = "20260927_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_table("route_results")
    op.drop_table("route_requests")


def downgrade() -> None:
    # 0b92552ee0d7의 정의 그대로 복원
    op.create_table(
        "route_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("start_latitude", sa.Float(), nullable=False),
        sa.Column("start_longitude", sa.Float(), nullable=False),
        sa.Column("end_latitude", sa.Float(), nullable=False),
        sa.Column("end_longitude", sa.Float(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "route_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("route_request_id", sa.Integer(), nullable=False),
        sa.Column("path_node_ids", sa.JSON(), nullable=False),
        sa.Column("total_weight", sa.Float(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["route_request_id"], ["route_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_request_id", name="uq_route_results_route_request_id"),
    )
