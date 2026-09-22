"""mova `chat`에 LLM 응답 본문 `reply` 칼럼 추가 (2026-09-22)

운영 응답을 학습 자료로 모으기 위해서다. 지금까지 학습에 쓸 수 있는 건
`chat`(질문)과 `picks`(추천 카드)뿐이고 응답 본문은 로그인 대화의
`chat_messages`에만 남아 Gemini/EXAONE이 쓴 intro가 대부분 유실됐다.
추천 트랙은 0편 안내로 바꾸기 전의 LLM 원문을 저장한다(모델 행동 그대로).
기존 행은 NULL.

Revision ID: 20260922_0002
Revises: 20260922_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_0002"
down_revision: str | None = "20260922_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("chat", sa.Column("reply", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat", "reply")
