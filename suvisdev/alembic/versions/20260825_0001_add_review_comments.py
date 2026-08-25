"""add review_comments table (mova)

리뷰 1단 댓글 — 로그인 사용자만 작성, 본인 것만 삭제.
리뷰/사용자 삭제 시 댓글도 함께 삭제(CASCADE).

Revision ID: 20260825_0001
Revises: 20260821_0001
Create Date: 2026-08-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260825_0001"
down_revision: str | None = "20260821_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE review_comments (
            id SERIAL PRIMARY KEY,
            review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_review_comments_review_id ON review_comments (review_id)")
    op.execute("CREATE INDEX ix_review_comments_user_id ON review_comments (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE review_comments")
