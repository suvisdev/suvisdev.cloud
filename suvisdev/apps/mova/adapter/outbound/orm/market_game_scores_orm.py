"""미니게임 결과 저장 — 초성 게임·카드 뒤집기.

- game_type: 'chosung' | 'memory'
- stage: memory 단계(1~10). chosung은 NULL.
- score: 게임별 방향이 다름 — chosung 상위=크게, memory 상위=작게.
- hints_used: chosung 타이브레이커. memory는 0.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User


class MovaGameScore(MovaModel):
    __tablename__ = "game_scores"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 'chosung' | 'memory' — 형식 고정 코드라 String으로.
    game_type: Mapped[str] = mapped_column(String(16), nullable=False)
    stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
