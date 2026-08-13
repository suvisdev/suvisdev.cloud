"""랭킹 DTO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ChatTrendAggRowDto:
    """user_actions.click 윈도우 집계 1행 (movie 단위).

    2026-08-13: pick_count/hit_sum(=노출·hit 신호) → click_count(=실제 사용자
    클릭)로 대체. AI 검색 TOP은 노출이 아니라 클릭이 유일한 신호.
    """

    movie_id: int
    click_count: int


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
    release_year: int
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
