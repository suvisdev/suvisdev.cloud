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

from mova.adapter.inbound.api.v1.collections_router import collections_router  # noqa: E402
from mova.app.dtos.market_collections_dto import (  # noqa: E402
    CollectionDetailDto,
    CollectionListDto,
    CollectionListItemDto,
    CollectionMoviesDto,
)
from mova.app.dtos.studio_movies_dto import MovieListItemDto  # noqa: E402
from mova.dependencies.collections_provider import (  # noqa: E402
    get_create_collection_use_case,
    get_get_collection_use_case,
    get_list_collection_movies_use_case,
    get_list_collections_use_case,
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
                    release_year="2008",
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
        app.dependency_overrides[get_list_collection_movies_use_case] = (
            lambda: _FakeCollectionsUseCase()
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


if __name__ == "__main__":
    unittest.main()
