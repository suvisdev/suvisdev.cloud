"""UserTasteVectorRecomputeInteractor 단위 테스트.

세션 팩토리·ReviewsPgRepository·UserTasteVectorsPgRepository를 전부 mock으로
대체해서 인터랙터의 분기 로직(리뷰 0건/가중합 0 → cleared, 별점 가중 평균 계산,
recompute_missing 집계, get_for_user 통과)만 격리 검증한다.
"""

from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.app.dtos.platform_user_taste_vector_dto import (  # noqa: E402
    UserTasteVectorDto,
)
from mova.app.use_cases.platform_user_taste_vector_interactor import (  # noqa: E402
    UserTasteVectorRecomputeInteractor,
)

_REVIEWS_REPO_PATH = "mova.adapter.outbound.pg.market_reviews_pg_repository.ReviewsPgRepository"
_TASTE_REPO_PATH = (
    "mova.adapter.outbound.pg.platform_user_taste_vectors_pg_repository."
    "UserTasteVectorsPgRepository"
)


def _make_session_factory() -> MagicMock:
    """`async with factory() as session:` 을 흉내내는 팩토리 mock."""
    session = MagicMock()
    factory = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory


class UserTasteVectorRecomputeInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_recompute_for_user_cleared_when_no_reviews(self) -> None:
        factory = _make_session_factory()
        reviews_repo = MagicMock()
        reviews_repo.list_embedded_reviews_by_user = AsyncMock(return_value=[])
        taste_repo = MagicMock()
        taste_repo.upsert = AsyncMock()

        interactor = UserTasteVectorRecomputeInteractor(session_factory=factory)
        with (
            patch(_REVIEWS_REPO_PATH, return_value=reviews_repo),
            patch(_TASTE_REPO_PATH, return_value=taste_repo),
        ):
            outcome = await interactor.recompute_for_user(1)

        self.assertEqual(outcome, "cleared")
        taste_repo.upsert.assert_awaited_once_with(1, None, 0)

    async def test_recompute_for_user_cleared_when_weights_sum_zero(self) -> None:
        factory = _make_session_factory()
        reviews_repo = MagicMock()
        # rating 0짜리만 있으면 weights_sum <= 0 → cleared
        reviews_repo.list_embedded_reviews_by_user = AsyncMock(return_value=[(1, 0.0, [1.0, 2.0])])
        taste_repo = MagicMock()
        taste_repo.upsert = AsyncMock()

        interactor = UserTasteVectorRecomputeInteractor(session_factory=factory)
        with (
            patch(_REVIEWS_REPO_PATH, return_value=reviews_repo),
            patch(_TASTE_REPO_PATH, return_value=taste_repo),
        ):
            outcome = await interactor.recompute_for_user(2)

        self.assertEqual(outcome, "cleared")
        taste_repo.upsert.assert_awaited_once_with(2, None, 0)

    async def test_recompute_for_user_updated_computes_rating_weighted_average(self) -> None:
        factory = _make_session_factory()
        reviews_repo = MagicMock()
        reviews_repo.list_embedded_reviews_by_user = AsyncMock(
            return_value=[(1, 4.0, [1.0, 2.0]), (2, 2.0, [3.0, 4.0])]
        )
        taste_repo = MagicMock()
        taste_repo.upsert = AsyncMock()

        interactor = UserTasteVectorRecomputeInteractor(session_factory=factory)
        with (
            patch(_REVIEWS_REPO_PATH, return_value=reviews_repo),
            patch(_TASTE_REPO_PATH, return_value=taste_repo),
        ):
            outcome = await interactor.recompute_for_user(3)

        self.assertEqual(outcome, "updated")
        # sum(rating*embedding) / sum(rating) = [(4*1+2*3)/6, (4*2+2*4)/6] = [10/6, 16/6]
        taste_repo.upsert.assert_awaited_once_with(3, [10.0 / 6.0, 16.0 / 6.0], 2)

    async def test_recompute_missing_aggregates_outcomes(self) -> None:
        factory = _make_session_factory()
        taste_repo = MagicMock()
        taste_repo.list_user_ids_with_rated_reviews = AsyncMock(return_value=[1, 2])

        interactor = UserTasteVectorRecomputeInteractor(session_factory=factory)
        with (
            patch(_TASTE_REPO_PATH, return_value=taste_repo),
            patch.object(
                interactor,
                "recompute_for_user",
                AsyncMock(side_effect=["updated", "cleared"]),
            ) as recompute_mock,
        ):
            stats = await interactor.recompute_missing(limit=None)

        self.assertEqual(stats, {"updated": 1, "cleared": 1})
        self.assertEqual(
            recompute_mock.await_args_list, [unittest.mock.call(1), unittest.mock.call(2)]
        )

    async def test_get_for_user_returns_none_when_no_row(self) -> None:
        factory = _make_session_factory()
        taste_repo = MagicMock()
        taste_repo.get_by_user_id = AsyncMock(return_value=None)

        interactor = UserTasteVectorRecomputeInteractor(session_factory=factory)
        with patch(_TASTE_REPO_PATH, return_value=taste_repo):
            result = await interactor.get_for_user(99)

        self.assertIsNone(result)

    async def test_get_for_user_passes_through_dto(self) -> None:
        factory = _make_session_factory()
        dto = UserTasteVectorDto(
            user_id=1, vector=[0.1, 0.2], review_count=2, updated_at=datetime.now(UTC)
        )
        taste_repo = MagicMock()
        taste_repo.get_by_user_id = AsyncMock(return_value=dto)

        interactor = UserTasteVectorRecomputeInteractor(session_factory=factory)
        with patch(_TASTE_REPO_PATH, return_value=taste_repo):
            result = await interactor.get_for_user(1)

        self.assertIs(result, dto)


if __name__ == "__main__":
    unittest.main()
