"""@see suvisdev/_claude/ENTITY_RULE.md — 영화↔인물(배우) 연결."""

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel


class MovaCharacter(MovaModel):
    """��ȭ?�ι� ���� (`characters` ���̺�). PK `id` ? `(movie_id, actor_id)` UNIQUE."""

    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("movie_id", "actor_id", name="uq_characters_movie_actor"),)

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
