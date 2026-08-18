"""컬렉션 Output Port — PgRepository가 구현한다."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_collections_dto import (
    CollectionAssignResultDto,
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

    @abstractmethod
    async def assign_movies(
        self, slug: str, movie_ids: list[int]
    ) -> CollectionAssignResultDto | None:
        """movie_ids의 `movies.collection_id`를 이 컬렉션으로 SET.

        one-to-many라 다른 컬렉션에 이미 속한 영화는 자동 이동(덮어쓰기).
        DB에 없는 movie_id는 skipped_ids에 담아 반환(부분 성공).
        컬렉션이 없으면 None.
        """

    @abstractmethod
    async def unassign_movies(
        self, slug: str, movie_ids: list[int]
    ) -> CollectionAssignResultDto | None:
        """movie_ids 중 이 컬렉션에 속한 영화만 collection_id를 NULL로 되돌린다.

        이 컬렉션에 속하지 않은 movie_id(다른 컬렉션 소속 또는 어디에도 없음)는
        skipped_ids에 담아 반환(idempotent, 조용히 무시).
        컬렉션이 없으면 None.
        """
