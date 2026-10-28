"""관리자 "운영 제어" 4단계 — mova·길들 점검 모드 `site_maintenance` (2026-10-28)

서비스마다 한 행(service = "mova" | "gildle"). enabled=true 면 백엔드가 그 서비스 API 를
503 으로 막고 웹은 점검 안내를 띄운다. 노트북·집컴 파드가 같은 값을 봐야 해서 DB 에 둔다.
행이 없으면 점검 아님(코드가 기본값으로 읽는다).

Revision ID: 20261028_0001
Revises: 20261007_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0001"
down_revision: str | None = "20261007_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "site_maintenance",
        sa.Column("service", sa.String(32), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("site_maintenance")
