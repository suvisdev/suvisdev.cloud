"""@see suvisdev/_claude/ENTITY_RULE.md — 영화 정보 (HOT 랭킹·상세용)."""

import re

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel

AGE_RATINGS = ("전체", "12세", "15세", "청불")


def slugify_movie(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title.strip().lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:64] or "movie"


class MovaMovie(MovaModel):
    """영화 카탈로그. PK `id` — 상세·랭킹·태그의 `movie_id` FK 참조."""

    __tablename__ = "movies"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    release_year: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    poster_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    platforms: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment='[{"provider": "netflix", "url": null, "type": "subscription"}]',
    )
    age_rating: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        index=True,
        comment="전체|12세|15세|청불",
    )
    genres: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    collection_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
