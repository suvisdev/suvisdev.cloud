"""movies.vote_count 추가 — rating=5.0 소수평가 노이즈 완화용 가중 정렬 시그널.

Revision ID: 20260901_0001
Revises: 20260831_0003
"""

from __future__ import annotations

from alembic import op

revision: str = "20260901_0001"
down_revision: str | None = "20260831_0003"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE movies ADD COLUMN IF NOT EXISTS vote_count INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE movies DROP COLUMN IF EXISTS vote_count")
