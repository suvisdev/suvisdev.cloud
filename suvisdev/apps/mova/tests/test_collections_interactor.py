from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.app.dtos.market_collections_dto import (  # noqa: E402
    CollectionCreateCommand,
    CollectionDetailDto,
    CollectionListDto,
    CollectionListItemDto,
    CollectionMoviesDto,
)
from mova.app.use_cases.collections_interactor import CollectionsInteractor  # noqa: E402


class _FakeRepository:
    def __init__(self) -> None:
        self.created: CollectionCreateCommand | None = None

    async def create(self, command: CollectionCreateCommand) -> CollectionDetailDto:
        self.created = command
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

    async def get_by_slug(self, slug: str) -> CollectionDetailDto | None:
        if slug == "missing":
            return None
        return CollectionDetailDto(
            id=1,
            slug=slug,
            name="컬렉션",
            description="설명",
            movie_count=2,
        )

    async def list_movies_by_slug(
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
            collection_name="컬렉션",
            items=[],
            total=0,
            limit=limit,
            offset=offset,
        )


class CollectionsInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_collection_delegates_to_repository(self) -> None:
        repo = _FakeRepository()
        interactor = CollectionsInteractor(repository=repo)

        cmd = CollectionCreateCommand.from_payload(
            slug="dark-knight-trilogy",
            name="다크 나이트 트릴로지",
            description="배트맨 시리즈",
        )
        dto = await interactor.create_collection(cmd)

        self.assertIsNotNone(repo.created)
        assert repo.created is not None
        self.assertEqual(str(repo.created.slug), "dark-knight-trilogy")
        self.assertEqual(dto.slug, "dark-knight-trilogy")

    async def test_list_collections_returns_paginated_dto(self) -> None:
        interactor = CollectionsInteractor(repository=_FakeRepository())
        dto = await interactor.list_collections(limit=10, offset=0)

        self.assertEqual(dto.total, 1)
        self.assertEqual(dto.limit, 10)
        self.assertEqual(dto.items[0].movie_count, 3)

    async def test_not_found_cases_return_none(self) -> None:
        interactor = CollectionsInteractor(repository=_FakeRepository())
        self.assertIsNone(await interactor.get_collection("missing"))
        self.assertIsNone(await interactor.list_collection_movies("missing", limit=20, offset=0))


if __name__ == "__main__":
    unittest.main()
