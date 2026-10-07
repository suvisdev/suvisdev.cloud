"""mova 랭킹(2026-10-07) — 영화 상세 열람(비로그인 포함)을 사람·영화·하루 1회로 세고 최근 7일 순위.

DB 쿼리는 운영 Postgres에서 확인하고, 여기서는 정책(누구를 어떤 키로 세나, 봇·조작 값 제외,
mova 랭킹 탭은 스냅샷이 아니라 바로 집계)과 공개 엔드포인트의 신원 처리를 고정한다.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.security.require_user import UserPrincipal, optional_user  # noqa: E402

from mova.adapter.inbound.api.v1.market_rankings_router import market_rankings_router  # noqa: E402
from mova.app.dtos.market_rankings_dto import RankingListDto  # noqa: E402
from mova.app.use_cases.market_rankings_interactor import (  # noqa: E402
    RankingsInteractor,
    viewer_key,
)
from mova.dependencies.market_rankings_provider import get_rankings_use_case  # noqa: E402

_UUID = "0b7f4c1e-8a3d-4f2b-9c6e-1d2a3b4c5d6e"
_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
)


class ViewerKeyTests(unittest.TestCase):
    def test_keys(self) -> None:
        self.assertEqual(viewer_key(7, _UUID), "u7")  # 로그인이면 사용자로(방문자 ID 무시)
        self.assertEqual(viewer_key(None, _UUID), f"v{_UUID}")
        self.assertIsNone(viewer_key(None, "not-a-uuid"))  # 조작된 값은 안 센다
        self.assertIsNone(viewer_key(None, None))


class RecordViewTests(unittest.IsolatedAsyncioTestCase):
    async def test_records_once_per_person_with_kst_date(self) -> None:
        repo = AsyncMock()
        repo.record_view.return_value = True
        ok = await RankingsInteractor(repo).record_view(
            5, user_id=None, visitor_id=_UUID, user_agent=_CHROME
        )
        self.assertTrue(ok)
        movie_id, key, day = repo.record_view.await_args.args
        self.assertEqual((movie_id, key), (5, f"v{_UUID}"))
        self.assertIsInstance(day, date)

    async def test_bots_and_unidentified_are_skipped(self) -> None:
        repo = AsyncMock()
        interactor = RankingsInteractor(repo)
        for kwargs in [
            {"user_id": None, "visitor_id": _UUID, "user_agent": "Googlebot/2.1"},
            {"user_id": None, "visitor_id": _UUID, "user_agent": None},
            {"user_id": None, "visitor_id": None, "user_agent": _CHROME},
        ]:
            self.assertFalse(await interactor.record_view(5, **kwargs))  # type: ignore[arg-type]
        repo.record_view.assert_not_awaited()


class GetHotTests(unittest.IsolatedAsyncioTestCase):
    async def test_mova_ranking_is_live_view_count(self) -> None:
        repo = AsyncMock()
        repo.get_view_ranking.return_value = RankingListDto(items=[], source="chat_trend")
        await RankingsInteractor(repo).get_hot("chat_trend", 20)
        repo.get_view_ranking.assert_awaited_once_with(7, 20)
        repo.get_hot.assert_not_awaited()

    async def test_box_office_still_uses_snapshot(self) -> None:
        repo = AsyncMock()
        repo.get_hot.return_value = RankingListDto(items=[], source="box_office")
        await RankingsInteractor(repo).get_hot("box_office", 20)
        repo.get_hot.assert_awaited_once_with("box_office", 20)
        repo.get_view_ranking.assert_not_awaited()


class ViewEndpointTests(unittest.TestCase):
    def _client(self, principal: UserPrincipal | None) -> tuple[TestClient, AsyncMock]:
        use_case = AsyncMock()
        app = FastAPI()
        app.include_router(market_rankings_router)
        app.dependency_overrides[get_rankings_use_case] = lambda: use_case
        app.dependency_overrides[optional_user] = lambda: principal
        return TestClient(app), use_case

    def test_anonymous_view_uses_visitor_id(self) -> None:
        client, use_case = self._client(None)
        res = client.post(
            "/rankings/views",
            json={"movie_id": 5, "visitor_id": _UUID},
            headers={"user-agent": _CHROME},
        )
        self.assertEqual(res.status_code, 204)
        kwargs = use_case.record_view.await_args.kwargs
        self.assertEqual((kwargs["user_id"], kwargs["visitor_id"]), (None, _UUID))
        self.assertEqual(kwargs["user_agent"], _CHROME)

    def test_logged_in_identity_comes_from_token(self) -> None:
        client, use_case = self._client(UserPrincipal(user_id=3, username="t"))
        client.post("/rankings/views", json={"movie_id": 5, "visitor_id": _UUID})
        self.assertEqual(use_case.record_view.await_args.kwargs["user_id"], 3)

    def test_bad_movie_id_rejected(self) -> None:
        client, use_case = self._client(None)
        self.assertEqual(client.post("/rankings/views", json={"movie_id": 0}).status_code, 422)
        use_case.record_view.assert_not_awaited()
