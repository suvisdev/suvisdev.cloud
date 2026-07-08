"""컬렉션 Interactor — 컬렉션 유스케이스 포트 구현체."""

from __future__ import annotations

from mova.app.dtos.market_collections_dto import (
    CollectionCreateCommand,
    CollectionDetailDto,
    CollectionListDto,
    CollectionMoviesDto,
)
from mova.app.ports.input.collections_use_case import (
    CreateCollectionUseCase,
    GetCollectionUseCase,
    ListCollectionMoviesUseCase,
    ListCollectionsUseCase,
)
from mova.app.ports.output.market_collections_repository import CollectionRepositoryPort


class CollectionsInteractor(
    CreateCollectionUseCase,
    ListCollectionsUseCase,
    GetCollectionUseCase,
    ListCollectionMoviesUseCase,
):
    def __init__(self, repository: CollectionRepositoryPort) -> None:
        self._repository = repository

    async def create_collection(self, command: CollectionCreateCommand) -> CollectionDetailDto:
        return await self._repository.create(command)

    async def list_collections(self, *, limit: int, offset: int) -> CollectionListDto:
        return await self._repository.list_collections(limit=limit, offset=offset)

    async def get_collection(self, slug: str) -> CollectionDetailDto | None:
        return await self._repository.get_by_slug(slug)

    async def list_collection_movies(
        self,
        slug: str,
        *,
        limit: int,
        offset: int,
    ) -> CollectionMoviesDto | None:
        return await self._repository.list_movies_by_slug(
            slug,
            limit=limit,
            offset=offset,
        )
