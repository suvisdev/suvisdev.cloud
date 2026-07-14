"""@see suvisdev/_claude/ENTITY_RULE.md — 영화 정보 (HOT 랭킹·상세용)."""

import re
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel

AGE_RATINGS = ("전체", "12세", "15세", "청불")

# Gemini text-embedding-004 기준 차원 (mova가 이미 Gemini 어댑터 사용 중, MOVA_ERD.md v3 확정).
_EMBEDDING_DIM = 768


def slugify_movie(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title.strip().lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:64] or "movie"


class MovaMovie(MovaModel):
    """영화 카탈로그. PK `id` — 상세·랭킹·태그의 `movie_id` FK 참조."""

    __tablename__ = "movies"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    release_year: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(_EMBEDDING_DIM),
        nullable=True,
        comment="추천용 임베딩. HNSW/IVFFlat 인덱스는 별도 리비전",
    )
    collection_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True,
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
