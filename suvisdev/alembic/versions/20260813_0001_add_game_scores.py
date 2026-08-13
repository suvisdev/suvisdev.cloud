"""add game_scores table (mova)

미니게임(초성·카드 뒤집기) 결과 저장. 로그인 사용자만 저장, 익명은 저장 안 함.

- game_type: 'chosung' | 'memory'
- stage: memory 게임 단계(1~10). chosung은 NULL.
- score: 게임별 정렬 방향이 다름.
  * chosung: 1분 안에 맞춘 개수(내림차순=상위)
  * memory: 완료까지 걸린 초(오름차순=상위)
- hints_used: chosung 타이브레이커(적게 쓸수록 상위). memory는 항상 0.

리더보드 조회에 필요한 복합 인덱스만 두고, 개인 기록 조회용도 겸함.

Revision ID: 20260813_0001
Revises: 20260812_0002
Create Date: 2026-08-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260813_0001"
down_revision: str | None = "20260812_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE game_scores (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            game_type VARCHAR(16) NOT NULL,
            stage INTEGER,
            score INTEGER NOT NULL,
            hints_used INTEGER NOT NULL DEFAULT 0,
            played_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_game_scores_type_stage_score "
        "ON game_scores (game_type, stage, score DESC)"
    )
    op.execute(
        "CREATE INDEX ix_game_scores_user_type_stage "
        "ON game_scores (user_id, game_type, stage)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS game_scores")
