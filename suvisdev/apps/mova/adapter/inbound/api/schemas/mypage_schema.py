from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PickHistorySchema(BaseModel):
    pick_id: int
    title: str
    hook: str | None
    slug: str
    poster_url: str | None
    batch_at: datetime
    feedback: str | None


class SearchHistorySchema(BaseModel):
    refined_query: str
    searched_at: datetime


class MyReviewSchema(BaseModel):
    review_id: int
    movie_id: int
    title: str
    slug: str
    poster_url: str | None
    rating: float | None
    body: str | None
    updated_at: datetime
    spoiler_spans: list[dict[str, Any]] = []


class ActivitySummarySchema(BaseModel):
    watched_count: int
    review_count: int
    average_rating: float | None


class MypageSchema(BaseModel):
    nickname: str | None
    preferred_genres: list[str]
    recent_picks: list[PickHistorySchema]
    recent_searches: list[SearchHistorySchema]
    my_reviews: list[MyReviewSchema]
    activity: ActivitySummarySchema
