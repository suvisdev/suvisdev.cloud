from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.api.v1.market_reviews_router import market_reviews_router  # noqa: E402
from mova.app.dtos.market_reviews_dto import (  # noqa: E402
    MovieRatingSummaryDto,
    ReviewActivityDto,
    ReviewDto,
    ReviewWithUserDto,
)
from mova.app.use_cases.market_reviews_interactor import ReviewsInteractor  # noqa: E402
from mova.dependencies.market_reviews_provider import get_reviews_use_case  # noqa: E402
from shared.security.require_user import UserPrincipal, require_user  # noqa: E402

_NOW = datetime(2026, 7, 31, tzinfo=UTC)


class _FakeReviewsUseCase:
    """ReviewsUseCase 포트를 그대로 구현하는 fake — 라우터 단위 테스트용."""

    def __init__(self, *, existing_review: ReviewDto | None = None) -> None:
        self.existing_review = existing_review
        self.update_review_calls: list[tuple[int, float | None, str | None]] = []

    async def add_activity(self, user_id: int, movie_id: int, action_type: str) -> ReviewActivityDto:
        return ReviewActivityDto(
            id=1, user_id=user_id, movie_id=movie_id, action_type=action_type, action_at=_NOW
        )

    async def add_review(self, user_id: int, movie_id: int, rating: float, body: str) -> ReviewDto:
        return ReviewDto(id=1, user_id=user_id, movie_id=movie_id, rating=rating, body=body, action_at=_NOW)

    async def get_by_id(self, review_id: int) -> ReviewDto | None:
        return self.existing_review

    async def get_by_movie(self, movie_id: int, limit: int, offset: int) -> list[ReviewWithUserDto]:
        return []

    async def update_review(
        self, review_id: int, rating: float | None, body: str | None
    ) -> ReviewDto | None:
        self.update_review_calls.append((review_id, rating, body))
        if self.existing_review is None:
            return None
        return ReviewDto(
            id=review_id,
            user_id=self.existing_review.user_id,
            movie_id=self.existing_review.movie_id,
            rating=rating if rating is not None else self.existing_review.rating,
            body=body if body is not None else self.existing_review.body,
            action_at=_NOW,
        )

    async def get_rating_summary(self, movie_id: int) -> MovieRatingSummaryDto:
        return MovieRatingSummaryDto(movie_id=movie_id, average_rating=0.0, review_count=0)


def _build_client(use_case: _FakeReviewsUseCase, *, principal: UserPrincipal | None) -> TestClient:
    app = FastAPI()
    app.include_router(market_reviews_router)
    app.dependency_overrides[get_reviews_use_case] = lambda: use_case
    if principal is not None:
        app.dependency_overrides[require_user] = lambda: principal
    return TestClient(app)


class ReviewsRouterAuthTests(unittest.TestCase):
    def test_add_review_without_token_returns_401(self) -> None:
        client = _build_client(_FakeReviewsUseCase(), principal=None)

        resp = client.post("/reviews", json={"movie_id": 1, "rating": 4.0, "body": "좋아요"})

        self.assertEqual(resp.status_code, 401)

    def test_add_activity_without_token_returns_401(self) -> None:
        client = _build_client(_FakeReviewsUseCase(), principal=None)

        resp = client.post("/reviews/activity", json={"movie_id": 1, "action_type": "watched"})

        self.assertEqual(resp.status_code, 401)

    def test_patch_without_token_returns_401(self) -> None:
        client = _build_client(_FakeReviewsUseCase(), principal=None)

        resp = client.patch("/reviews/1", json={"rating": 5.0})

        self.assertEqual(resp.status_code, 401)

    def test_add_review_uses_principal_user_id_not_body(self) -> None:
        use_case = _FakeReviewsUseCase()
        principal = UserPrincipal(user_id=42, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.post("/reviews", json={"movie_id": 1, "rating": 4.0, "body": "좋아요"})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["user_id"], 42)


class ReviewsRouterOwnershipTests(unittest.TestCase):
    def test_patch_other_users_review_returns_403(self) -> None:
        owner_review = ReviewDto(id=1, user_id=1, movie_id=10, rating=3.0, body="원본", action_at=_NOW)
        use_case = _FakeReviewsUseCase(existing_review=owner_review)
        attacker = UserPrincipal(user_id=2, username="attacker")
        client = _build_client(use_case, principal=attacker)

        resp = client.patch("/reviews/1", json={"rating": 5.0})

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(use_case.update_review_calls, [])

    def test_patch_missing_review_returns_404(self) -> None:
        use_case = _FakeReviewsUseCase(existing_review=None)
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.patch("/reviews/999", json={"rating": 5.0})

        self.assertEqual(resp.status_code, 404)

    def test_patch_own_review_succeeds(self) -> None:
        owner_review = ReviewDto(id=1, user_id=1, movie_id=10, rating=3.0, body="원본", action_at=_NOW)
        use_case = _FakeReviewsUseCase(existing_review=owner_review)
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.patch("/reviews/1", json={"rating": 5.0, "body": "수정"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(use_case.update_review_calls, [(1, 5.0, "수정")])


class ReviewsInteractorUpsertTests(unittest.IsolatedAsyncioTestCase):
    """UNIQUE(user_id, movie_id) 재작성이 IntegrityError로 새지 않고 upsert되는지."""

    async def test_add_review_inserts_when_no_existing_review(self) -> None:
        repo = AsyncMock()
        repo.find_by_user_and_movie.return_value = None
        repo.add_review.return_value = ReviewDto(
            id=1, user_id=1, movie_id=10, rating=4.0, body="신규", action_at=_NOW
        )
        interactor = ReviewsInteractor(repository=repo)

        result = await interactor.add_review(1, 10, 4.0, "신규")

        repo.add_review.assert_awaited_once_with(1, 10, 4.0, "신규")
        repo.update_review.assert_not_awaited()
        self.assertEqual(result.body, "신규")

    async def test_add_review_updates_existing_instead_of_duplicate_insert(self) -> None:
        existing = ReviewDto(id=7, user_id=1, movie_id=10, rating=3.0, body="원본", action_at=_NOW)
        repo = AsyncMock()
        repo.find_by_user_and_movie.return_value = existing
        repo.update_review.return_value = ReviewDto(
            id=7, user_id=1, movie_id=10, rating=5.0, body="재작성", action_at=_NOW
        )
        interactor = ReviewsInteractor(repository=repo)

        result = await interactor.add_review(1, 10, 5.0, "재작성")

        repo.add_review.assert_not_awaited()
        repo.update_review.assert_awaited_once_with(7, 5.0, "재작성")
        self.assertEqual(result.id, 7)
        self.assertEqual(result.body, "재작성")


if __name__ == "__main__":
    unittest.main()
