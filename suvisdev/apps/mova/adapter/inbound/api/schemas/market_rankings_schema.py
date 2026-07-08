"""랭킹 HTTP 스키마."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class RankingItemSchema(BaseModel):
    rank: int
    movie_id: int
    chat_id: int | None = None
    score: int | None = None
    badge: str | None = None


class RankingBulkSchema(BaseModel):
    ranked_at: date | None = None
    source: str = "box_office"
    items: list[RankingItemSchema] = Field(default_factory=list)


class HotRankingDisplaySchema(BaseModel):
    id: int
    rank: int
    movie_id: int
    chat_id: int | None
    source: str
    score: int | None
    badge: str | None
    ranked_at: date
    refined_query: str | None
    slug: str
    title: str
    release_year: str
    rating: float
    poster: str
    platform: str | None
    genres: list[str]


class HotRankingListSchema(BaseModel):
    source: str
    items: list[HotRankingDisplaySchema]


class RefreshRankingResponseSchema(BaseModel):
    source: str
    ranked_at: date
    saved: int
