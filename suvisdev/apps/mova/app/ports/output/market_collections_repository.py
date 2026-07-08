"""컬렉션 Output Port — PgRepository가 구현한다."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_collections_dto import (
    CollectionCreateCommand,
    CollectionDetailDto,
    CollectionListDto,
    CollectionMoviesDto,
)


class CollectionRepositoryPort(ABC):
    @abstractmethod
    async def create(self, command: CollectionCreateCommand) -> CollectionDetailDto:
        """컬렉션 생성."""

    @abstractmethod
    async def list_collections(self, *, limit: int, offset: int) -> CollectionListDto:
        """컬렉션 목록 조회."""

    @abstractmethod
    async def get_by_slug(self, slug: str) -> CollectionDetailDto | None:
        """slug로 컬렉션 상세 조회 (소속 영화 수 포함)."""

    @abstractmethod
    async def list_movies_by_slug(
        self,
        slug: str,
        *,
        limit: int,
        offset: int,
    ) -> CollectionMoviesDto | None:
        """컬렉션 slug로 소속 영화 목록 조회. 컬렉션이 없으면 None."""
