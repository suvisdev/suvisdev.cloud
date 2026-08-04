"""리뷰 Interactor — ReviewsUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.market_reviews_dto import (
    MovieRatingSummaryDto,
    ReviewActivityDto,
    ReviewDto,
    ReviewWithUserDto,
)
from mova.app.ports.input.market_reviews_use_case import ReviewsUseCase
from mova.app.ports.output.market_reviews_errors import ReviewNotWatchedError, ReviewValidationError
from mova.app.ports.output.market_reviews_repository import ReviewsRepositoryPort


class ReviewsInteractor(ReviewsUseCase):
    def __init__(self, repository: ReviewsRepositoryPort) -> None:
        self._repository = repository

    async def add_activity(
        self, user_id: int, movie_id: int, action_type: str
    ) -> ReviewActivityDto:
        return await self._repository.add_activity(user_id, movie_id, action_type)

    async def add_review(
        self, user_id: int, movie_id: int, rating: float | None, body: str | None
    ) -> ReviewDto:
        """UNIQUE(user_id, movie_id) 위반을 IntegrityError로 새지 않게 upsert로 처리한다.

        재제출 = 수정(단일 리뷰 폼 전제) — 기존 리뷰가 있으면 갱신, 없으면 신규 작성.
        별점만/본문만/둘 다 허용하고, 완전히 빈 제출(둘 다 없음)만 거부한다.
        watched(시청) 기록이 없으면 거부한다 — rating 존재 여부로 판정하지 않는다
        (순환 논리 방지: rating 자체가 이 메서드로 저장되므로).
        """
        if not await self._repository.has_watched(user_id, movie_id):
            raise ReviewNotWatchedError("시청(watched) 표시를 먼저 해야 리뷰를 남길 수 있습니다.")
        if rating is None and not (body and body.strip()):
            raise ReviewValidationError("별점 또는 감상평 중 하나는 입력해야 합니다.")
        existing = await self._repository.find_by_user_and_movie(user_id, movie_id)
        if existing is None:
            return await self._repository.add_review(user_id, movie_id, rating, body)
        updated = await self._repository.update_review(existing.id, rating, body)
        return updated if updated is not None else existing

    async def get_by_id(self, review_id: int) -> ReviewDto | None:
        return await self._repository.get_by_id(review_id)

    async def get_by_movie(self, movie_id: int, limit: int, offset: int) -> list[ReviewWithUserDto]:
        return await self._repository.get_by_movie(movie_id, limit, offset)

    async def update_review(
        self, review_id: int, rating: float | None, body: str | None
    ) -> ReviewDto | None:
        return await self._repository.update_review(review_id, rating, body)

    async def get_rating_summary(self, movie_id: int) -> MovieRatingSummaryDto:
        return await self._repository.get_rating_summary(movie_id)
