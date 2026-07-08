"""@see suvisdev/_claude/ENTITY_RULE.md — 사용자↔영화 반응·별점 리뷰(단일 테이블 `reviews`)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User

ACTION_FAVORITE = "favorite"
ACTION_WATCHED = "watched"
ACTION_CLICK = "click"
ACTION_NOT_INTERESTED = "not_interested"
ACTION_REVIEW = "review"

EVENT_ACTION_TYPES = frozenset(
    {
        ACTION_FAVORITE,
        ACTION_WATCHED,
        ACTION_CLICK,
        ACTION_NOT_INTERESTED,
    },
)


class MovaReview(MovaModel):
    """사용자↔ 영화 반응·리뷰. PK `id` — 이벤트는 중복 허용, 별점 리뷰는 user+movie당 1건."""

    __tablename__ = "reviews"

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
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
