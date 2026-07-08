"""영화 HTTP 요청/응답 Pydantic 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── 공용 중첩 스키마 ──────────────────────────────────────────────────────────


class PlatformSchema(BaseModel):
    provider: str
    url: str | None = None
    type: str | None = None


class ActorInMovieSchema(BaseModel):
    character_id: int
    actor_id: int
    name: str
    role_type: Literal["director", "actor"]
    profile_photo_url: str


class TagInMovieSchema(BaseModel):
    id: int
    tag_kind: Literal["mood", "genre", "cast"]
    slug: str
    label: str
    description: str
    character_id: int | None


# ── 영화 상세 응답 (GET /movies/{slug}) ──────────────────────────────────────


class MovieDetailSchema(BaseModel):
    id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    platforms: list[PlatformSchema]
    age_rating: str | None
    genres: list[str]
    collection_id: int | None
    actors: list[ActorInMovieSchema]
    tags: list[TagInMovieSchema]


# ── 목록 응답 (GET /movies) ──────────────────────────────────────────────────


class MovieListItemSchema(BaseModel):
    id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    platforms: list[PlatformSchema]
    age_rating: str | None
    genres: list[str]


class MovieListSchema(BaseModel):
    items: list[MovieListItemSchema]
    total: int
    limit: int
    offset: int


# ── 생성 요청 (import/admin 용) ──────────────────────────────────────────────


class MovieCreateSchema(BaseModel):
    title: str
    slug: str | None = None
    release_year: str = ""
    rating: float = 0.0
    poster_url: str = ""
    platforms: list[PlatformSchema] = Field(default_factory=list)
    age_rating: str | None = None
    genres: list[str] = Field(default_factory=list)
    collection_id: int | None = None


class MovieTitleCreateSchema(BaseModel):
    title: str
