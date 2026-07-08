from __future__ import annotations

from datetime import datetime

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


class MypageSchema(BaseModel):
    nickname: str | None
    preferred_genres: list[str]
    recent_picks: list[PickHistorySchema]
    recent_searches: list[SearchHistorySchema]
