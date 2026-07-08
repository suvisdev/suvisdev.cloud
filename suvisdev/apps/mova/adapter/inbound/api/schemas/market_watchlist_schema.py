from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WatchlistAddSchema(BaseModel):
    user_id: int
    movie_id: int


class WatchlistItemSchema(BaseModel):
    movie_id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str | None
    added_at: datetime


class WatchlistSchema(BaseModel):
    items: list[WatchlistItemSchema]
    total: int
