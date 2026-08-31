"""@see suvisdev/_claude/ENTITY_RULE.md — 영화 정보 (HOT 랭킹·상세용)."""

import re
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel

AGE_RATINGS = ("전체", "12세", "15세", "청불")

# 카탈로그/추천 노출 허용 언어(TMDB original_language, ISO 639-1) — 태국어 등
# 한국어 서비스 이용자에게 맥락 없는 외국어 영화 노출 방지(2026-08-07).
# original_language가 아직 채워지지 않은(None) 레거시 로우는 백필 전까지
# 노출 유지(미확인을 배제로 취급하지 않음) — movies_pg_repository.list_movies(),
# market_chat_pg_repository.py 후보 쿼리에서 함께 참조한다.
ALLOWED_ORIGINAL_LANGUAGES = ("ko", "en")

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
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    platforms: Mapped[list[Any]] = mapped_column(
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
    original_language: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        index=True,
        comment="TMDB original_language(ISO 639-1). 카탈로그/추천 언어 필터용",
    )
    origin_country: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='TMDB origin_country(ISO 3166-1 alpha-2 배열). 공동제작이면 ["US","GB"]',
    )
    trailer_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="TMDB videos의 YouTube 트레일러 video key. https://www.youtube.com/embed/{key}로 조립",
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
