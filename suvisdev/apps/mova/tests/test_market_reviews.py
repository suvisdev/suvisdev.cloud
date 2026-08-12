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
from mova.app.ports.output.market_reviews_errors import (  # noqa: E402
    ReviewNotWatchedError,
    ReviewValidationError,
)
from mova.app.use_cases.market_reviews_interactor import ReviewsInteractor  # noqa: E402
from mova.dependencies.market_reviews_provider import get_reviews_use_case  # noqa: E402
from mova.dependencies.platform_user_taste_vector_provider import (  # noqa: E402
    get_user_taste_vector_recompute_use_case,
)
from mova.dependencies.review_embedding_provider import (  # noqa: E402
    get_review_embedding_backfill_use_case,
)
from mova.dependencies.review_spoiler_provider import (  # noqa: E402
    get_review_spoiler_backfill_use_case,
)
from shared.security.require_user import UserPrincipal, require_user  # noqa: E402

_NOW = datetime(2026, 7, 31, tzinfo=UTC)


class _FakeReviewsUseCase:
    """ReviewsUseCase 포트를 그대로 구현하는 fake — 라우터 단위 테스트용."""

    def __init__(self, *, existing_review: ReviewDto | None = None) -> None:
        self.existing_review = existing_review
        self.update_review_calls: list[tuple[int, float | None, str | None]] = []
        self.delete_review_calls: list[int] = []

    async def add_activity(self, user_id: int, movie_id: int, action_type: str) -> ReviewActivityDto:
        return ReviewActivityDto(
            id=1, user_id=user_id, movie_id=movie_id, action_type=action_type, action_at=_NOW
        )

    async def add_review(
        self, user_id: int, movie_id: int, rating: float | None, body: str | None
    ) -> ReviewDto:
        if rating is None and not (body and body.strip()):
            raise ReviewValidationError("별점 또는 감상평 중 하나는 입력해야 합니다.")
        return ReviewDto(
            id=1, user_id=user_id, movie_id=movie_id, rating=rating or 0, body=body or "", action_at=_NOW
        )

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

    async def delete_review(self, review_id: int) -> bool:
        self.delete_review_calls.append(review_id)
        return self.existing_review is not None


class _FakeEmbeddingBackfill:
    """add_review/update_review가 BackgroundTasks에 add_task로 넘기는 인터랙터의 fake.

    테스트 스코프에서는 실제 세션 팩토리·Gemini를 부르지 않는 게 목적이다 —
    호출 여부만 여기서 확인하지 않는다(백그라운드 임베딩 트리거 검증은 별도
    파일 `test_review_embedding_backfill.py`에서 인터랙터 단위로 다룬다).
    """

    def __init__(self) -> None:
        self.embed_one_calls: list[int] = []

    async def embed_one(self, review_id: int) -> str:
        self.embed_one_calls.append(review_id)
        return "skipped"


class _FakeTasteRecompute:
    """add_review/update_review가 BG에 넘기는 취향 벡터 재계산 인터랙터의 fake."""

    def __init__(self) -> None:
        self.recompute_calls: list[int] = []

    async def recompute_for_user(self, user_id: int) -> str:
        self.recompute_calls.append(user_id)
        return "updated"


class _FakeSpoilerBackfill:
    """add_review/update_review가 BG에 넘기는 스포일러 감지 인터랙터의 fake."""

    def __init__(self) -> None:
        self.detect_calls: list[int] = []

    async def detect_one(self, review_id: int) -> str:
        self.detect_calls.append(review_id)
        return "skipped"


def _build_client(use_case: _FakeReviewsUseCase, *, principal: UserPrincipal | None) -> TestClient:
    app = FastAPI()
    app.include_router(market_reviews_router)
    app.dependency_overrides[get_reviews_use_case] = lambda: use_case
    app.dependency_overrides[get_review_embedding_backfill_use_case] = _FakeEmbeddingBackfill
    app.dependency_overrides[get_user_taste_vector_recompute_use_case] = _FakeTasteRecompute
    app.dependency_overrides[get_review_spoiler_backfill_use_case] = _FakeSpoilerBackfill
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

    def test_delete_without_token_returns_401(self) -> None:
        client = _build_client(_FakeReviewsUseCase(), principal=None)

        resp = client.delete("/reviews/1")

        self.assertEqual(resp.status_code, 401)

    def test_add_review_uses_principal_user_id_not_body(self) -> None:
        use_case = _FakeReviewsUseCase()
        principal = UserPrincipal(user_id=42, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.post("/reviews", json={"movie_id": 1, "rating": 4.0, "body": "좋아요"})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["user_id"], 42)


class ReviewsRouterPhaseBTests(unittest.TestCase):
    """Phase B — 별점만/본문만/둘 다 제출, 완전히 빈 제출은 422."""

    def test_rating_only_returns_201(self) -> None:
        use_case = _FakeReviewsUseCase()
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.post("/reviews", json={"movie_id": 1, "rating": 4.0})

        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.json()["body"])

    def test_body_only_returns_201(self) -> None:
        use_case = _FakeReviewsUseCase()
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.post("/reviews", json={"movie_id": 1, "body": "좋아요"})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["body"], "좋아요")

    def test_both_empty_returns_422(self) -> None:
        use_case = _FakeReviewsUseCase()
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.post("/reviews", json={"movie_id": 1})

        self.assertEqual(resp.status_code, 422)

    def test_rating_out_of_range_returns_422(self) -> None:
        use_case = _FakeReviewsUseCase()
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.post("/reviews", json={"movie_id": 1, "rating": 5.5})

        self.assertEqual(resp.status_code, 422)

    def test_rating_not_half_step_returns_422(self) -> None:
        use_case = _FakeReviewsUseCase()
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.post("/reviews", json={"movie_id": 1, "rating": 4.2})

        self.assertEqual(resp.status_code, 422)


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


class ReviewsRouterDeleteTests(unittest.TestCase):
    def test_delete_other_users_review_returns_403(self) -> None:
        owner_review = ReviewDto(id=1, user_id=1, movie_id=10, rating=3.0, body="원본", action_at=_NOW)
        use_case = _FakeReviewsUseCase(existing_review=owner_review)
        attacker = UserPrincipal(user_id=2, username="attacker")
        client = _build_client(use_case, principal=attacker)

        resp = client.delete("/reviews/1")

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(use_case.delete_review_calls, [])

    def test_delete_missing_review_returns_404(self) -> None:
        use_case = _FakeReviewsUseCase(existing_review=None)
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.delete("/reviews/999")

        self.assertEqual(resp.status_code, 404)

    def test_delete_own_review_succeeds(self) -> None:
        owner_review = ReviewDto(id=1, user_id=1, movie_id=10, rating=3.0, body="원본", action_at=_NOW)
        use_case = _FakeReviewsUseCase(existing_review=owner_review)
        principal = UserPrincipal(user_id=1, username="tester")
        client = _build_client(use_case, principal=principal)

        resp = client.delete("/reviews/1")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(use_case.delete_review_calls, [1])

    def test_admin_can_delete_other_users_review(self) -> None:
        owner_review = ReviewDto(id=1, user_id=1, movie_id=10, rating=3.0, body="원본", action_at=_NOW)
        use_case = _FakeReviewsUseCase(existing_review=owner_review)
        admin = UserPrincipal(user_id=99, username="admin", role="admin")
        client = _build_client(use_case, principal=admin)

        resp = client.delete("/reviews/1")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(use_case.delete_review_calls, [1])


class ReviewsInteractorUpsertTests(unittest.IsolatedAsyncioTestCase):
    """UNIQUE(user_id, movie_id) 재작성이 IntegrityError로 새지 않고 upsert되는지."""

    async def test_add_review_inserts_when_no_existing_review(self) -> None:
        repo = AsyncMock()
        repo.has_watched.return_value = True
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
        repo.has_watched.return_value = True
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


class ReviewsInteractorPhaseBTests(unittest.IsolatedAsyncioTestCase):
    """인터랙터 레벨 — 별점만/본문만 허용, 완전히 빈 제출만 거부."""

    async def test_rejects_when_both_rating_and_body_missing(self) -> None:
        repo = AsyncMock()
        repo.has_watched.return_value = True
        interactor = ReviewsInteractor(repository=repo)

        with self.assertRaises(ReviewValidationError):
            await interactor.add_review(1, 10, None, None)
        repo.find_by_user_and_movie.assert_not_awaited()

    async def test_rejects_when_body_is_blank_string(self) -> None:
        repo = AsyncMock()
        repo.has_watched.return_value = True
        interactor = ReviewsInteractor(repository=repo)

        with self.assertRaises(ReviewValidationError):
            await interactor.add_review(1, 10, None, "   ")

    async def test_allows_rating_only(self) -> None:
        repo = AsyncMock()
        repo.has_watched.return_value = True
        repo.find_by_user_and_movie.return_value = None
        repo.add_review.return_value = ReviewDto(
            id=1, user_id=1, movie_id=10, rating=4.0, body="", action_at=_NOW
        )
        interactor = ReviewsInteractor(repository=repo)

        await interactor.add_review(1, 10, 4.0, None)

        repo.add_review.assert_awaited_once_with(1, 10, 4.0, None)

    async def test_allows_body_only(self) -> None:
        repo = AsyncMock()
        repo.has_watched.return_value = True
        repo.find_by_user_and_movie.return_value = None
        repo.add_review.return_value = ReviewDto(
            id=1, user_id=1, movie_id=10, rating=0, body="좋아요", action_at=_NOW
        )
        interactor = ReviewsInteractor(repository=repo)

        await interactor.add_review(1, 10, None, "좋아요")

        repo.add_review.assert_awaited_once_with(1, 10, None, "좋아요")


class ReviewsInteractorWatchedGateTests(unittest.IsolatedAsyncioTestCase):
    """watched 게이트 — rating을 판정 근거로 쓰지 않고 has_watched만 본다."""

    async def test_rejects_when_not_watched_even_with_valid_content(self) -> None:
        repo = AsyncMock()
        repo.has_watched.return_value = False
        interactor = ReviewsInteractor(repository=repo)

        with self.assertRaises(ReviewNotWatchedError):
            await interactor.add_review(1, 10, 5.0, "재밌어요")
        repo.find_by_user_and_movie.assert_not_awaited()
        repo.add_review.assert_not_awaited()

    async def test_allows_when_watched(self) -> None:
        repo = AsyncMock()
        repo.has_watched.return_value = True
        repo.find_by_user_and_movie.return_value = None
        repo.add_review.return_value = ReviewDto(
            id=1, user_id=1, movie_id=10, rating=5.0, body="재밌어요", action_at=_NOW
        )
        interactor = ReviewsInteractor(repository=repo)

        result = await interactor.add_review(1, 10, 5.0, "재밌어요")

        repo.has_watched.assert_awaited_once_with(1, 10)
        self.assertEqual(result.body, "재밌어요")


if __name__ == "__main__":
    unittest.main()
