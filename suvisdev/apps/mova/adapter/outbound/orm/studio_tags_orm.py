"""@see suvisdev/_claude/ENTITY_RULE.md — 영화별 키워드 태그 (감성·장르·등장인물)."""

import re
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel

TAG_KIND_MOOD = "mood"
TAG_KIND_GENRE = "genre"
TAG_KIND_CAST = "cast"
TAG_KINDS = frozenset({TAG_KIND_MOOD, TAG_KIND_GENRE, TAG_KIND_CAST})


def slugify_tag(label: str) -> str:
    s = re.sub(r"[^\w\s-]", "", label.strip().lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:64] or "tag"


class MovaTag(MovaModel):
    """영화 키워드: 감성(mood), 장르(genre), 등장인물(cast).

    (tag_kind, slug) 전역 UNIQUE는 넣지 않는다 — mood/genre는 같은 slug(예: genre-SF)를
    여러 영화가 공유하는 "영화당 1행" 조인 테이블 구조라 전역 UNIQUE를 걸면 두 번째
    영화부터 태깅이 막힌다(MOVA_ERD.md v3 R5는 이 구조를 반영하지 못한 오류로 판단해 보류).
    """

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("movie_id", "slug", name="uq_tags_movie_slug"),
        UniqueConstraint("character_id", name="uq_tags_character_id"),
        CheckConstraint(
            "(character_id IS NULL) != (movie_id IS NULL)",
            name="ck_tags_exactly_one_target",
        ),
    )

    movie_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    character_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="cast 태그일 때 characters.id (영화-인물 유도)",
    )
    tag_kind: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=TAG_KIND_MOOD,
        index=True,
        comment="mood | genre | cast",
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
