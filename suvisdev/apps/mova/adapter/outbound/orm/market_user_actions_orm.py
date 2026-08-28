"""@see suvisdev/_claude/ENTITY_RULE.md — 사용자↔영화 행동 이벤트 로그(`user_actions`). reviews와 분리."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User

ACTION_FAVORITE = "favorite"
ACTION_WATCHED = "watched"
ACTION_CLICK = "click"
ACTION_NOT_INTERESTED = "not_interested"
# 2026-08-28 채팅 3트랙: 단순 질의는 트렌드 미집계, 아래 두 신호(예매 의지·
# 평가 후 긍정 반응)만 chat_trend에 반영한다는 사용자 결정의 저장 형태.
ACTION_BOOKING_INTENT = "booking_intent"
ACTION_EVAL_POSITIVE = "eval_positive"

EVENT_ACTION_TYPES = frozenset(
    {
        ACTION_FAVORITE,
        ACTION_WATCHED,
        ACTION_CLICK,
        ACTION_NOT_INTERESTED,
        ACTION_BOOKING_INTENT,
        ACTION_EVAL_POSITIVE,
    },
)


class MovaUserAction(MovaModel):
    """사용자↔영화 행동 이벤트. PK `id` — 행동 로그는 중복 허용(UNIQUE 없음)."""

    __tablename__ = "user_actions"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Viewer users.id (동일 DB FK)",
    )
    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
