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

EVENT_ACTION_TYPES = frozenset(
    {
        ACTION_FAVORITE,
        ACTION_WATCHED,
        ACTION_CLICK,
        ACTION_NOT_INTERESTED,
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
