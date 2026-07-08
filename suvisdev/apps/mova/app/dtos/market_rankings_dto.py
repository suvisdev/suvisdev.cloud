"""랭킹 DTO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ChatTrendAggRowDto:
    """picks×chat 윈도우 집계 1행 (movie 단위 raw 수치)."""

    movie_id: int
    pick_count: int
    hit_sum: int


@dataclass(frozen=True)
class ChatTrendRankingRowDto:
    """rankings(source=chat_trend) 스냅샷 저장 1행."""

    rank: int
    movie_id: int
    chat_id: int | None
    score: int
    badge: str | None


@dataclass(frozen=True)
class RankingItemDto:
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
    genres: list[str]

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_rankings_schema import HotRankingDisplaySchema

        return HotRankingDisplaySchema(
            id=self.id,
            rank=self.rank,
            movie_id=self.movie_id,
            chat_id=self.chat_id,
            source=self.source,
            score=self.score,
            badge=self.badge,
            ranked_at=self.ranked_at,
            refined_query=self.refined_query,
            slug=self.slug,
            title=self.title,
            release_year=self.release_year,
            rating=self.rating,
            poster=self.poster,
            platform=None,
            genres=self.genres,
        )


@dataclass(frozen=True)
class RankingListDto:
    items: list[RankingItemDto]
    source: str

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_rankings_schema import HotRankingListSchema

        return HotRankingListSchema(
            source=self.source,
            items=[item.to_schema() for item in self.items],
        )
