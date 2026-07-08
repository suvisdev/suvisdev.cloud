"""컬렉션 Input Port — Router가 의존하는 추상 계약."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_collections_dto import (
    CollectionCreateCommand,
    CollectionDetailDto,
    CollectionListDto,
    CollectionMoviesDto,
)


class CreateCollectionUseCase(ABC):
    @abstractmethod
    async def create_collection(self, command: CollectionCreateCommand) -> CollectionDetailDto:
        """컬렉션 생성."""


class ListCollectionsUseCase(ABC):
    @abstractmethod
    async def list_collections(self, *, limit: int, offset: int) -> CollectionListDto:
        """컬렉션 목록 조회."""


class GetCollectionUseCase(ABC):
    @abstractmethod
    async def get_collection(self, slug: str) -> CollectionDetailDto | None:
        """컬렉션 단건 조회. 없으면 None."""


class ListCollectionMoviesUseCase(ABC):
    @abstractmethod
    async def list_collection_movies(
        self,
        slug: str,
        *,
        limit: int,
        offset: int,
    ) -> CollectionMoviesDto | None:
        """컬렉션에 속한 영화 목록. 컬렉션이 없으면 None."""
