"""mypage 라우터 인증·소유권 가드 테스트.

2026-08-07 이전엔 가드가 없어 user_id만 알면 남의 닉네임·AI 추천 기록·검색
기록을 볼 수 있었다(프로덕션에서 실제 재현 확인). 리뷰·시청 통계까지 응답에
추가하면서 함께 잠갔고, 그 상태를 이 테스트로 고정한다.
"""

from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from shared.security.require_user import UserPrincipal, require_user  # noqa: E402

from mova.adapter.inbound.api.v1.mypage_router import mypage_router  # noqa: E402
from mova.app.dtos.mypage_dto import ActivitySummary, MypageDto  # noqa: E402
from mova.dependencies.mypage_provider import get_mypage_use_case  # noqa: E402

_NOW = datetime(2026, 8, 7, tzinfo=UTC)


class _FakeMypageUseCase:
    def __init__(self) -> None:
        self.called_with: list[int] = []

    async def get_mypage(self, user_id: int) -> MypageDto:
        self.called_with.append(user_id)
        return MypageDto(
            nickname="태기",
            preferred_genres=["SF"],
            recent_picks=[],
            recent_searches=[],
            my_reviews=[],
            activity=ActivitySummary(watched_count=3, review_count=2, average_rating=4.25),
        )


def _build_client(use_case: _FakeMypageUseCase, *, principal: UserPrincipal | None) -> TestClient:
    app = FastAPI()
    app.include_router(mypage_router)
    app.dependency_overrides[get_mypage_use_case] = lambda: use_case
    if principal is not None:
        app.dependency_overrides[require_user] = lambda: principal
    return TestClient(app)


class MypageRouterAuthTests(unittest.TestCase):
    def test_without_token_returns_401(self) -> None:
        use_case = _FakeMypageUseCase()
        client = _build_client(use_case, principal=None)

        resp = client.get("/mypage/1")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(use_case.called_with, [])

    def test_other_users_mypage_returns_403(self) -> None:
        """남의 user_id를 넣으면 데이터를 조회조차 하지 않아야 한다."""
        use_case = _FakeMypageUseCase()
        client = _build_client(use_case, principal=UserPrincipal(user_id=7, username="tester"))

        resp = client.get("/mypage/1")

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(use_case.called_with, [])

    def test_own_mypage_returns_200_with_activity(self) -> None:
        use_case = _FakeMypageUseCase()
        client = _build_client(use_case, principal=UserPrincipal(user_id=7, username="tester"))

        resp = client.get("/mypage/7")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["activity"]["watched_count"], 3)
        self.assertEqual(body["activity"]["review_count"], 2)
        self.assertEqual(body["activity"]["average_rating"], 4.25)
        self.assertEqual(body["my_reviews"], [])
        self.assertEqual(use_case.called_with, [7])

    def test_non_positive_user_id_returns_400(self) -> None:
        use_case = _FakeMypageUseCase()
        client = _build_client(use_case, principal=UserPrincipal(user_id=0, username="tester"))

        resp = client.get("/mypage/0")

        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
