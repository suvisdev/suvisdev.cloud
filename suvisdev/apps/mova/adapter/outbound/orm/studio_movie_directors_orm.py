"""@see suvisdev/_claude/ENTITY_RULE.md — 영화-감독 관계."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel


class MovaMovieDirector(MovaModel):
    """영화-감독 관계 (`movie_directors` 테이블). PK `id` — `(movie_id, actor_id)` UNIQUE (공동 감독 허용).

    characters와 대칭 구조 — character_name이 필요 없어(배역이 아니라 감독) 별도
    테이블로 분리했다. actors.role_type='director'로 배우/감독을 이미 구분하므로
    이 테이블은 "어느 영화를 누가 감독했는지" 관계만 담는다.
    """

    __tablename__ = "movie_directors"
    __table_args__ = (
        UniqueConstraint("movie_id", "actor_id", name="uq_movie_directors_movie_actor"),
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
