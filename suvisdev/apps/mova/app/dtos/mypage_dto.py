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
class MyReviewItem:
    """내가 쓴 리뷰 1건 + 대상 영화 표시 정보.

    `reviews`는 별점만/본문만 제출도 허용하므로(2026-07-31) 둘 다 nullable이다.
    """

    review_id: int
    movie_id: int
    title: str
    slug: str
    poster_url: str | None
    rating: float | None
    body: str | None
    updated_at: datetime


@dataclass
class ActivitySummary:
    """마이페이지 활동 요약. 별점을 매긴 리뷰가 없으면 average_rating은 None."""

    watched_count: int
    review_count: int
    average_rating: float | None


@dataclass
class MypageDto:
    nickname: str | None
    preferred_genres: list[str]
    recent_picks: list[PickHistoryItem]
    recent_searches: list[SearchHistoryItem]
    my_reviews: list[MyReviewItem]
    activity: ActivitySummary

    def to_schema(self) -> MypageSchema:
        from mova.adapter.inbound.api.schemas.mypage_schema import (
            ActivitySummarySchema,
            MypageSchema,
            MyReviewSchema,
            PickHistorySchema,
            SearchHistorySchema,
        )

        return MypageSchema(
            nickname=self.nickname,
            preferred_genres=self.preferred_genres,
            my_reviews=[
                MyReviewSchema(
                    review_id=r.review_id,
                    movie_id=r.movie_id,
                    title=r.title,
                    slug=r.slug,
                    poster_url=r.poster_url,
                    rating=r.rating,
                    body=r.body,
                    updated_at=r.updated_at,
                )
                for r in self.my_reviews
            ],
            activity=ActivitySummarySchema(
                watched_count=self.activity.watched_count,
                review_count=self.activity.review_count,
                average_rating=self.activity.average_rating,
            ),
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
