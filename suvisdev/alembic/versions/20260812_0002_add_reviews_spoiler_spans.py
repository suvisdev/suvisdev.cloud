"""add reviews.spoiler_spans column (mova)

리뷰 본문에서 스포일러로 판단된 문구 스팬 목록을 저장. 프론트에서 이 스팬을
가려두고 클릭 시 확인 다이얼로그로 노출.

포맷: JSONB list of {"start": int, "end": int, "text": str}. start/end는 body
문자열의 문자 인덱스(파이썬 슬라이스 규칙 그대로).

Revision ID: 20260812_0002
Revises: 20260812_0001
Create Date: 2026-08-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260812_0002"
down_revision: str | None = "20260812_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE reviews ADD COLUMN spoiler_spans JSONB NOT NULL DEFAULT '[]'::jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS spoiler_spans")
