"""2026-09-11 리뷰 H4 — mova 쓰기 트리거 엔드포인트 admin 가드 회귀 고정.

- POST /mova/collections: 익명 컬렉션 생성(공개 목록 노출·스팸) 차단
- POST /mova/rankings/refresh: 익명 스냅샷 delete+insert 반복 트리거 차단
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from mova.adapter.inbound.api.v1.collections_router import collections_router  # noqa: E402
from mova.adapter.inbound.api.v1.market_rankings_router import (  # noqa: E402
    market_rankings_router,
)
from mova.dependencies.collections_provider import (  # noqa: E402
    get_create_collection_use_case,
)
from mova.dependencies.market_rankings_provider import (  # noqa: E402
    get_generate_chat_trend_ranking_use_case,
)


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(collections_router, prefix="/mova")
    app.include_router(market_rankings_router, prefix="/mova")
    app.dependency_overrides[get_create_collection_use_case] = lambda: MagicMock()
    app.dependency_overrides[get_generate_chat_trend_ranking_use_case] = lambda: MagicMock()
    return app


class AdminGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(_make_app())

    def test_create_collection_rejects_anonymous(self) -> None:
        res = self.client.post(
            "/mova/collections", json={"slug": "spam", "name": "스팸", "description": ""}
        )
        self.assertEqual(res.status_code, 401)

    def test_refresh_rankings_rejects_anonymous(self) -> None:
        self.assertEqual(self.client.post("/mova/rankings/refresh").status_code, 401)


if __name__ == "__main__":
    unittest.main()
