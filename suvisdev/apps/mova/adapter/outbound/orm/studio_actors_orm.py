"""@see suvisdev/_claude/ENTITY_RULE.md — 인물(감독·배우) 정보."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel


class MovaActor(MovaModel):
    """인물(배우·감독) 정보. PK `id` — UNIQUE는 `tmdb_person_id`(upsert 키, 동명이인 구분용)."""

    __tablename__ = "actors"
    __table_args__ = (UniqueConstraint("tmdb_person_id", name="uq_actors_tmdb_person_id"),)

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role_type: Mapped[str] = mapped_column(String(16), nullable=False, default="actor", index=True)
    profile_photo_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tmdb_person_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="TMDB person id — upsert 키. 이름만으로는 동명이인을 구분 못 함",
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
