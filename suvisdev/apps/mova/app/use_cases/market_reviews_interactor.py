"""리뷰 Interactor — ReviewsUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.market_reviews_dto import (
    MovieRatingSummaryDto,
    ReviewActivityDto,
    ReviewDto,
    ReviewWithUserDto,
)
from mova.app.ports.input.market_reviews_use_case import ReviewsUseCase
from mova.app.ports.output.market_reviews_repository import ReviewsRepositoryPort


class ReviewsInteractor(ReviewsUseCase):
    def __init__(self, repository: ReviewsRepositoryPort) -> None:
        self._repository = repository

    async def add_activity(
        self, user_id: int, movie_id: int, action_type: str
    ) -> ReviewActivityDto:
        return await self._repository.add_activity(user_id, movie_id, action_type)

    async def add_review(self, user_id: int, movie_id: int, rating: float, body: str) -> ReviewDto:
        return await self._repository.add_review(user_id, movie_id, rating, body)

    async def get_by_movie(self, movie_id: int, limit: int, offset: int) -> list[ReviewWithUserDto]:
        return await self._repository.get_by_movie(movie_id, limit, offset)

    async def update_review(
        self, review_id: int, rating: float | None, body: str | None
    ) -> ReviewDto | None:
        return await self._repository.update_review(review_id, rating, body)

    async def get_rating_summary(self, movie_id: int) -> MovieRatingSummaryDto:
        return await self._repository.get_rating_summary(movie_id)
