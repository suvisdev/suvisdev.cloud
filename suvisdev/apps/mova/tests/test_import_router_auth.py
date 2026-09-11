"""`/mova/import/tmdb`·`/import/kofic` 어드민 가드 — 보안 백로그 🟡(2026-09-09).

익명 사용자가 카탈로그 쓰기(TMDB 수입·KOFIC 랭킹 갱신)를 트리거할 수 있던
무인증 쓰기 엔드포인트를 `require_admin`으로 잠근다. 가드 없이 통과되면
외부인이 카탈로그를 오염시키거나 외부 API 쿼터를 소모시킬 수 있다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from shared.security.require_admin import AdminPrincipal, require_admin  # noqa: E402

from mova.adapter.inbound.api.v1.import_router import import_router  # noqa: E402
from mova.app.dtos.market_box_office_dto import KoficImportCommand  # noqa: E402
from mova.app.dtos.studio_import_dto import (  # noqa: E402
    MovieImportResultDto,
    StudioImportQuery,
    StudioImportResponse,
    TmdbImportCommand,
)
from mova.app.ports.input.import_use_case import ImportUseCase  # noqa: E402
from mova.dependencies.import_provider import get_import_use_case  # noqa: E402


class _FakeImportUseCase(ImportUseCase):
    async def introduce_myself(self, query: StudioImportQuery) -> StudioImportResponse:
        return StudioImportResponse(id=query.id, name=query.name)

    async def seed_catalog_if_sparse(self) -> MovieImportResultDto:
        return MovieImportResultDto(imported=0)

    async def import_tmdb(self, command: TmdbImportCommand) -> MovieImportResultDto:
        return MovieImportResultDto(imported=1, movie_ids=[42])

    async def import_kofic_boxoffice(self, command: KoficImportCommand) -> MovieImportResultDto:
        return MovieImportResultDto(imported=1, movie_ids=[42], rankings_updated=True)


def _make_app(*, admin: bool) -> FastAPI:
    app = FastAPI()
    app.include_router(import_router, prefix="/mova")
    app.dependency_overrides[get_import_use_case] = lambda: _FakeImportUseCase()
    if admin:
        app.dependency_overrides[require_admin] = lambda: AdminPrincipal(
            user_id=1, username="admin"
        )
    return app


class ImportRouterAuthTests(unittest.TestCase):
    """require_admin은 실제 구현을 태워 무토큰 401을 확인한다."""

    def test_import_tmdb_requires_admin(self) -> None:
        client = TestClient(_make_app(admin=False))
        res = client.post("/mova/import/tmdb", json={"tmdb_id": 1})
        self.assertEqual(res.status_code, 401)

    def test_import_kofic_requires_admin(self) -> None:
        client = TestClient(_make_app(admin=False))
        res = client.post("/mova/import/kofic", json={})
        self.assertEqual(res.status_code, 401)

    def test_import_tmdb_passes_with_admin(self) -> None:
        client = TestClient(_make_app(admin=True))
        res = client.post("/mova/import/tmdb", json={"tmdb_id": 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["imported"], 1)

    def test_import_kofic_passes_with_admin(self) -> None:
        client = TestClient(_make_app(admin=True))
        res = client.post("/mova/import/kofic", json={})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["rankings_updated"])


if __name__ == "__main__":
    unittest.main()
