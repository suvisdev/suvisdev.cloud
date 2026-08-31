"""review_votes 테이블 생성 — 리뷰 유용성 투표(도움돼요).

Revision ID: 20260831_0003
Revises: 20260831_0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0003"
down_revision: str | None = "20260831_0002"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "review_votes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "review_id",
            sa.Integer,
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "review_id", name="uq_review_votes_user_review"),
    )


def downgrade() -> None:
    op.drop_table("review_votes")
