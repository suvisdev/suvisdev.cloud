"""@see suvisdev/_claude/ENTITY_RULE.md — 영화-인물 관계."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel


class MovaCharacter(MovaModel):
    """영화-인물 관계 (`characters` 테이블). PK `id` — `(movie_id, actor_id, character_name)` UNIQUE (1인 다역 허용)."""

    __tablename__ = "characters"
    __table_args__ = (
        UniqueConstraint(
            "movie_id", "actor_id", "character_name", name="uq_characters_movie_actor_name"
        ),
    )

    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("actors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    character_name: Mapped[str] = mapped_column(Text, nullable=False)
    billing_order: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="TMDB credits.cast[].order — 주연/조연 순서(작을수록 비중 큼)",
    )
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
