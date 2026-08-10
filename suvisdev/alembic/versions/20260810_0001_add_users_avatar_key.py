"""add users.avatar_key TEXT column

S3 객체 key만 저장한다(예: "avatars/7/3f2b....webp" — 풀 URL이 아니다).
URL을 저장하지 않는 이유: 버킷이 비공개라 표시에는 presigned URL이 필요한데
그건 1시간짜리 만료값이라 DB에 넣으면 즉시 낡는다. 조회 시점에 key로
`Tank.generate_presigned_url()`을 새로 발급한다.

nullable=True — "아직 업로드 안 함"이 정상 상태다.

Revision ID: 20260810_0001
Revises: 20260809_0001
Create Date: 2026-08-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0001"
down_revision: str | None = "20260809_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_key")
