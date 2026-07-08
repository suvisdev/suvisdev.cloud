from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mova.adapter.inbound.api.schemas.mypage_schema import MypageSchema


@dataclass
class PickHistoryItem:
    pick_id: int
    title: str
    hook: str | None
    slug: str
    poster_url: str | None
    batch_at: datetime
    feedback: str | None


@dataclass
class SearchHistoryItem:
    refined_query: str
    searched_at: datetime


@dataclass
class MypageDto:
    nickname: str | None
    preferred_genres: list[str]
    recent_picks: list[PickHistoryItem]
    recent_searches: list[SearchHistoryItem]

    def to_schema(self) -> MypageSchema:
        from mova.adapter.inbound.api.schemas.mypage_schema import (
            MypageSchema,
            PickHistorySchema,
            SearchHistorySchema,
        )

        return MypageSchema(
            nickname=self.nickname,
            preferred_genres=self.preferred_genres,
            recent_picks=[
                PickHistorySchema(
                    pick_id=p.pick_id,
                    title=p.title,
                    hook=p.hook,
                    slug=p.slug,
                    poster_url=p.poster_url,
                    batch_at=p.batch_at,
                    feedback=p.feedback,
                )
                for p in self.recent_picks
            ],
            recent_searches=[
                SearchHistorySchema(refined_query=s.refined_query, searched_at=s.searched_at)
                for s in self.recent_searches
            ],
        )
