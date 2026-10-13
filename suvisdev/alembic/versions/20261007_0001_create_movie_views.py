"""create movie_views table (mova 랭킹 — 영화 상세 열람)

비로그인 포함 영화 상세 열람을 하루 1회(사람·영화·날짜)로 기록한다. "mova 랭킹" 탭이
최근 7일 열람 수로 순위를 매긴다(2026-10-07 사용자 결정). viewer_key: 로그인 "u<id>",
비로그인 "v<방문자 UUID>".

Revision ID: 20261007_0001
Revises: 20260930_0001
Create Date: 2026-10-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261007_0001"
down_revision: str | None = "20260930_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE movie_views (
            id SERIAL PRIMARY KEY,
            movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            viewer_key VARCHAR(64) NOT NULL,
            view_date DATE NOT NULL,
            viewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_movie_views_daily UNIQUE (movie_id, viewer_key, view_date)
        )
        """
    )
    op.execute("CREATE INDEX ix_movie_views_view_date ON movie_views (view_date)")
    op.execute("COMMENT ON COLUMN movie_views.view_date IS 'KST 날짜'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS movie_views")
