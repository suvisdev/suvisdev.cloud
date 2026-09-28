"""미니게임 — 인터랙터는 앱 예외(GamesError), 라우터가 HTTP 상태로 변환(§P, 2026-09-28)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

_ROOT = Path(__file__).resolve().parents[3]
for _p in (_ROOT, _ROOT / "apps"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from mova.adapter.inbound.api.v1.games_router import games_router  # noqa: E402
from mova.app.ports.output.games_errors import GamesError  # noqa: E402
from mova.app.use_cases.games_interactor import GamesInteractor  # noqa: E402
from mova.dependencies.games_provider import get_games_use_case  # noqa: E402


class GamesErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_interactor_raises_app_error_not_http(self) -> None:
        repo = AsyncMock()
        repo.sample_chosung_question.return_value = None
        with self.assertRaises(GamesError) as ctx:
            await GamesInteractor(repo).next_chosung_question("all")
        self.assertEqual(ctx.exception.status_code, 503)
        with self.assertRaises(GamesError) as ctx:
            await GamesInteractor(repo).memory_deck(11)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_router_maps_error_to_status(self) -> None:
        repo = AsyncMock()
        repo.sample_chosung_question.return_value = None
        app = FastAPI()
        app.include_router(games_router)
        app.dependency_overrides[get_games_use_case] = lambda: GamesInteractor(repo)
        res = TestClient(app).get("/games/chosung/next")
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()["detail"], "문제를 만들 영화가 부족합니다.")


if __name__ == "__main__":
    unittest.main()
