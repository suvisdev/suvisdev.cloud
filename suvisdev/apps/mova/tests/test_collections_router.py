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

from shared.security.require_admin import AdminPrincipal, require_admin  # noqa: E402

from mova.adapter.inbound.api.v1.collections_router import collections_router  # noqa: E402
from mova.app.dtos.market_collections_dto import (  # noqa: E402
    CollectionAssignResultDto,
    CollectionDetailDto,
    CollectionListDto,
    CollectionListItemDto,
    CollectionMoviesDto,
)
from mova.app.dtos.studio_movies_dto import MovieListItemDto  # noqa: E402
from mova.dependencies.collections_provider import (  # noqa: E402
    get_assign_movies_use_case,
    get_create_collection_use_case,
    get_get_collection_use_case,
    get_list_collection_movies_use_case,
    get_list_collections_use_case,
    get_unassign_movies_use_case,
)


class _FakeCollectionsUseCase:
    async def create_collection(self, command):  # type: ignore[no-untyped-def]
        if str(command.slug) == "duplicate":
            raise ValueError("Collection slug already exists: duplicate")
        return CollectionDetailDto(
            id=1,
            slug=str(command.slug),
            name=str(command.name),
            description=str(command.description),
            movie_count=0,
        )

    async def list_collections(self, *, limit: int, offset: int) -> CollectionListDto:
        return CollectionListDto(
            items=[
                CollectionListItemDto(
                    id=1,
                    slug="dark-knight-trilogy",
                    name="다크 나이트 트릴로지",
                    description="배트맨 시리즈",
                    movie_count=3,
                )
            ],
            total=1,
            limit=limit,
            offset=offset,
        )

    async def get_collection(self, slug: str) -> CollectionDetailDto | None:
        if slug == "missing":
            return None
        return CollectionDetailDto(
            id=1,
            slug=slug,
            name="다크 나이트 트릴로지",
            description="배트맨 시리즈",
            movie_count=3,
        )

    async def assign_movies(
        self, slug: str, movie_ids: list[int]
    ) -> CollectionAssignResultDto | None:
        if slug == "missing":
            return None
        # 90/91은 존재, 92는 없음(skipped). 90은 이미 다른 컬렉션 소속(moved).
        found = [m for m in movie_ids if m in {90, 91}]
        skipped = [m for m in movie_ids if m not in {90, 91}]
        moved = 1 if 90 in found else 0
        return CollectionAssignResultDto(
            collection_id=1,
            collection_slug=slug,
            affected=len(found),
            skipped_ids=skipped,
            moved_from_other_collection=moved,
        )

    async def unassign_movies(
        self, slug: str, movie_ids: list[int]
    ) -> CollectionAssignResultDto | None:
        if slug == "missing":
            return None
        # 90/91은 이 컬렉션 소속, 나머지는 skipped(다른 컬렉션 또는 없음).
        in_collection = [m for m in movie_ids if m in {90, 91}]
        skipped = [m for m in movie_ids if m not in {90, 91}]
        return CollectionAssignResultDto(
            collection_id=1,
            collection_slug=slug,
            affected=len(in_collection),
            skipped_ids=skipped,
            moved_from_other_collection=0,
        )

    async def list_collection_movies(
        self,
        slug: str,
        *,
        limit: int,
        offset: int,
    ) -> CollectionMoviesDto | None:
        if slug == "missing":
            return None
        return CollectionMoviesDto(
            collection_id=1,
            collection_slug=slug,
            collection_name="다크 나이트 트릴로지",
            items=[
                MovieListItemDto(
                    id=10,
                    slug="dark-knight",
                    title="다크 나이트",
                    release_year=2008,
                    rating=4.8,
                    poster_url="",
                    platforms=[],
                    age_rating=None,
                    genres=["액션"],
                )
            ],
            total=1,
            limit=limit,
            offset=offset,
        )


class CollectionsRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(collections_router, prefix="/mova")
        app.dependency_overrides[get_create_collection_use_case] = lambda: _FakeCollectionsUseCase()
        app.dependency_overrides[get_list_collections_use_case] = lambda: _FakeCollectionsUseCase()
        app.dependency_overrides[get_get_collection_use_case] = lambda: _FakeCollectionsUseCase()
        app.dependency_overrides[get_list_collection_movies_use_case] = lambda: (
            _FakeCollectionsUseCase()
        )
        app.dependency_overrides[get_assign_movies_use_case] = lambda: _FakeCollectionsUseCase()
        app.dependency_overrides[get_unassign_movies_use_case] = lambda: _FakeCollectionsUseCase()
        # 어드민 가드는 통과시킴 — 라우터의 배정/해제 자체 로직만 검증한다.
        app.dependency_overrides[require_admin] = lambda: AdminPrincipal(
            user_id=1, username="admin"
        )
        self.client = TestClient(app)

    def test_create_collection_success(self) -> None:
        res = self.client.post(
            "/mova/collections",
            json={
                "slug": "dark-knight-trilogy",
                "name": "다크 나이트 트릴로지",
                "description": "배트맨 시리즈",
            },
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["slug"], "dark-knight-trilogy")

    def test_create_collection_conflict(self) -> None:
        res = self.client.post(
            "/mova/collections",
            json={"slug": "duplicate", "name": "중복", "description": ""},
        )
        self.assertEqual(res.status_code, 409)

    def test_create_collection_invalid_slug_returns_422(self) -> None:
        res = self.client.post(
            "/mova/collections",
            json={"slug": "Bad Slug!", "name": "형식 오류", "description": ""},
        )
        self.assertEqual(res.status_code, 422)

    def test_get_collection_not_found(self) -> None:
        res = self.client.get("/mova/collections/missing")
        self.assertEqual(res.status_code, 404)

    def test_list_collections_with_pagination(self) -> None:
        res = self.client.get("/mova/collections?limit=5&offset=0")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["movie_count"], 3)

    def test_list_collection_movies_not_found(self) -> None:
        res = self.client.get("/mova/collections/missing/movies")
        self.assertEqual(res.status_code, 404)

    def test_assign_movies_partial_success_with_move(self) -> None:
        res = self.client.patch(
            "/mova/collections/nolan-world/movies",
            json={"movie_ids": [90, 91, 92]},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["affected"], 2)  # 90, 91
        self.assertEqual(body["skipped_ids"], [92])
        self.assertEqual(body["moved_from_other_collection"], 1)  # 90 이동

    def test_assign_movies_collection_not_found(self) -> None:
        res = self.client.patch(
            "/mova/collections/missing/movies",
            json={"movie_ids": [90]},
        )
        self.assertEqual(res.status_code, 404)

    def test_assign_movies_empty_body_returns_422(self) -> None:
        # movie_ids min_length=1 — 빈 리스트는 스키마 단계에서 거부.
        res = self.client.patch(
            "/mova/collections/nolan-world/movies",
            json={"movie_ids": []},
        )
        self.assertEqual(res.status_code, 422)

    def test_unassign_movies_partial_success(self) -> None:
        res = self.client.request(
            "DELETE",
            "/mova/collections/nolan-world/movies",
            json={"movie_ids": [90, 91, 99]},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["affected"], 2)  # 90, 91
        self.assertEqual(body["skipped_ids"], [99])
        self.assertEqual(body["moved_from_other_collection"], 0)

    def test_unassign_movies_collection_not_found(self) -> None:
        res = self.client.request(
            "DELETE",
            "/mova/collections/missing/movies",
            json={"movie_ids": [90]},
        )
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
