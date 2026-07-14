"""@see suvisdev/_claude/ENTITY_RULE.md — 사용자↔영화 별점·감상평 리뷰(단일 테이블 `reviews`)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User


class MovaReview(MovaModel):
    """사용자↔영화 별점·감상평. PK `id` — user+movie당 리뷰 1건 (수정은 UPDATE)."""

    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_reviews_user_movie"),)

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
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
