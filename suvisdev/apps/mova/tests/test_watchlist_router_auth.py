"""watchlist 라우터 인증·소유권 가드.

2026-08-07 이전엔 4개 엔드포인트 전부 무가드라 user_id만 알면 남의 찜 목록을
읽는 것은 물론 **추가·삭제까지** 가능했다(프로덕션 재현 확인).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.api.v1.market_watchlist_router import (  # noqa: E402
    market_watchlist_router,
)
from mova.app.dtos.market_watchlist_dto import WatchlistDto  # noqa: E402
from mova.dependencies.market_watchlist_provider import get_watchlist_use_case  # noqa: E402
from shared.security.require_user import UserPrincipal, require_user  # noqa: E402


class _FakeWatchlistUseCase:
    def __init__(self) -> None:
        self.added: list[tuple[int, int]] = []
        self.removed: list[tuple[int, int]] = []
        self.read: list[int] = []

    async def get_watchlist(self, user_id: int) -> WatchlistDto:
        self.read.append(user_id)
        return WatchlistDto(items=[])

    async def is_in_watchlist(self, user_id: int, movie_id: int) -> bool:
        self.read.append(user_id)
        return False

    async def add(self, user_id: int, movie_id: int) -> None:
        self.added.append((user_id, movie_id))

    async def remove(self, user_id: int, movie_id: int) -> None:
        self.removed.append((user_id, movie_id))


def _client(use_case, *, principal: UserPrincipal | None) -> TestClient:
    app = FastAPI()
    app.include_router(market_watchlist_router)
    app.dependency_overrides[get_watchlist_use_case] = lambda: use_case
    if principal is not None:
        app.dependency_overrides[require_user] = lambda: principal
    return TestClient(app)


class WatchlistAuthTests(unittest.TestCase):
    def test_all_endpoints_require_token(self) -> None:
        uc = _FakeWatchlistUseCase()
        c = _client(uc, principal=None)

        self.assertEqual(c.get("/watchlist/1").status_code, 401)
        self.assertEqual(c.get("/watchlist/1/check/2").status_code, 401)
        self.assertEqual(c.post("/watchlist", json={"user_id": 1, "movie_id": 2}).status_code, 401)
        self.assertEqual(c.delete("/watchlist/1/2").status_code, 401)

        # 가드가 없으면 use case까지 흘러갔을 요청들 — 하나도 도달하면 안 된다.
        self.assertEqual(uc.read, [])
        self.assertEqual(uc.added, [])
        self.assertEqual(uc.removed, [])

    def test_reading_other_users_list_is_forbidden(self) -> None:
        uc = _FakeWatchlistUseCase()
        c = _client(uc, principal=UserPrincipal(user_id=7, username="tester"))

        self.assertEqual(c.get("/watchlist/1").status_code, 403)
        self.assertEqual(c.get("/watchlist/1/check/2").status_code, 403)
        self.assertEqual(uc.read, [])

    def test_writing_to_other_users_list_is_forbidden(self) -> None:
        """가장 심각했던 부분 — 남의 찜에 추가·삭제가 됐다."""
        uc = _FakeWatchlistUseCase()
        c = _client(uc, principal=UserPrincipal(user_id=7, username="tester"))

        self.assertEqual(c.post("/watchlist", json={"user_id": 1, "movie_id": 2}).status_code, 403)
        self.assertEqual(c.delete("/watchlist/1/2").status_code, 403)
        self.assertEqual(uc.added, [])
        self.assertEqual(uc.removed, [])

    def test_own_list_works(self) -> None:
        uc = _FakeWatchlistUseCase()
        c = _client(uc, principal=UserPrincipal(user_id=7, username="tester"))

        self.assertEqual(c.get("/watchlist/7").status_code, 200)
        self.assertEqual(c.post("/watchlist", json={"user_id": 7, "movie_id": 2}).status_code, 201)
        self.assertEqual(c.delete("/watchlist/7/2").status_code, 200)
        self.assertEqual(uc.added, [(7, 2)])
        self.assertEqual(uc.removed, [(7, 2)])

    def test_admin_can_delete_other_users_item(self) -> None:
        uc = _FakeWatchlistUseCase()
        c = _client(uc, principal=UserPrincipal(user_id=99, username="admin", role="admin"))

        self.assertEqual(c.delete("/watchlist/1/2").status_code, 200)
        self.assertEqual(uc.removed, [(1, 2)])

    def test_admin_cannot_read_other_users_list(self) -> None:
        """관리자 우회는 삭제 한정 — 조회·추가는 여전히 본인만."""
        uc = _FakeWatchlistUseCase()
        c = _client(uc, principal=UserPrincipal(user_id=99, username="admin", role="admin"))

        self.assertEqual(c.get("/watchlist/1").status_code, 403)
        self.assertEqual(
            c.post("/watchlist", json={"user_id": 1, "movie_id": 2}).status_code, 403
        )


if __name__ == "__main__":
    unittest.main()
