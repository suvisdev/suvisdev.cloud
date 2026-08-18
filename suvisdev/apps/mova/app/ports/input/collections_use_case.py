"""컬렉션 Input Port — Router가 의존하는 추상 계약."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_collections_dto import (
    CollectionAssignResultDto,
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


class AssignMoviesUseCase(ABC):
    @abstractmethod
    async def assign_movies(
        self, slug: str, movie_ids: list[int]
    ) -> CollectionAssignResultDto | None:
        """movie_ids를 이 컬렉션으로 배정(one-to-many 덮어쓰기). 컬렉션 없으면 None."""


class UnassignMoviesUseCase(ABC):
    @abstractmethod
    async def unassign_movies(
        self, slug: str, movie_ids: list[int]
    ) -> CollectionAssignResultDto | None:
        """이 컬렉션에서 movie_ids 배정 해제(idempotent). 컬렉션 없으면 None."""
