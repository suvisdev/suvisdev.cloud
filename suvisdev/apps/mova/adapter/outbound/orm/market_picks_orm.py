"""@see suvisdev/_claude/ENTITY_RULE.md — AI 채팅 추천 작품 기록 (`picks`)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User


class MovaPick(MovaModel):
    """한 번의 AI 채팅 응답에서 추천된 작품 1건 (최대 3건/배치)."""

    __tablename__ = "picks"

    chat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(User.__table__.c.id, ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Viewer users.id (동일 DB FK, 비로그인은 NULL)",
    )
    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pick_rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="해당 배치 내 순위 1~3",
    )
    hook: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="추천 당시 제목 (DB slug 변경 대비 스냅샷)",
    )
    batch_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="동일 채팅 응답 3건 묶음 시각",
    )
    feedback: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        index=True,
        comment="like|dislike|null — 추천 자체에 대한 사용자 반응",
    )
