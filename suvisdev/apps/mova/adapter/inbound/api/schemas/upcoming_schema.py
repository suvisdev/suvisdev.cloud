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
