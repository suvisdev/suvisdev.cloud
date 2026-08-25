"""개봉예정작 스키마 — TMDB /movie/upcoming 프록시용."""

from __future__ import annotations

from pydantic import BaseModel


class UpcomingMovieSchema(BaseModel):
    tmdb_id: int
    slug: str
    title: str
    release_year: int
    release_date: str  # YYYY-MM-DD (일부 미정작은 빈 문자열)
    rating: float
    poster_url: str
    genres: list[str]
    overview: str


class UpcomingListSchema(BaseModel):
    region: str
    items: list[UpcomingMovieSchema]


class UpcomingActorSchema(BaseModel):
    name: str
    role_type: str
    profile_photo_url: str
    character_name: str | None = None


class UpcomingPlatformSchema(BaseModel):
    provider: str
    url: str | None = None


class UpcomingDetailSchema(BaseModel):
    """개봉 예정 영화 상세 — MovieDetailSchema와 호환되는 구조."""

    id: int
    slug: str
    title: str
    release_year: int
    rating: float
    poster_url: str
    platforms: list[UpcomingPlatformSchema]
    age_rating: str | None = None
    genres: list[str]
    synopsis: str | None = None
    trailer_key: str | None = None
    actors: list[UpcomingActorSchema]
    release_date: str = ""
