"""리뷰 유용성 투표(도움돼요) — `review_votes` 테이블."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User


class MovaReviewVote(MovaModel):
    """리뷰 1건에 대한 유용성 투표. 사용자당 리뷰당 1표(토글)."""

    __tablename__ = "review_votes"
    __table_args__ = (UniqueConstraint("user_id", "review_id", name="uq_review_votes_user_review"),)

    review_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Viewer users.id (동일 DB FK)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
