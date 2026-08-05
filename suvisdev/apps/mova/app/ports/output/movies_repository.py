"""영화 Output Port — PgRepository가 구현한다."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_import_dto import MovieUpsertCommand
from mova.app.dtos.studio_movies_dto import MovieDetailDto, MovieFilterQuery, MovieListDto


class MoviesRepositoryPort(ABC):
    @abstractmethod
    async def get_by_slug(self, slug: str) -> MovieDetailDto | None:
        """slug로 영화 상세 (출연진·태그 포함) 조회."""

    @abstractmethod
    async def find_by_title(self, title: str) -> MovieDetailDto | None:
        """제목 일치 영화 1건 (import/harvest 매칭용 — 채팅 추천 enrich는 find_by_id 사용)."""

    @abstractmethod
    async def find_by_id(self, movie_id: int) -> MovieDetailDto | None:
        """movie.id로 상세 조회 (채팅 추천 enrich용 — Gemini가 카탈로그에서 고른
        movie_id를 그대로 신뢰해 조회한다. title 문자열 재매칭은 하지 않는다)."""

    @abstractmethod
    async def list_movies(self, query: MovieFilterQuery) -> MovieListDto:
        """장르·연도·평점·연령등급·플랫폼 필터 + 정렬 + 페이지네이션."""

    @abstractmethod
    async def count_movies(self) -> int:
        """등록된 영화 총 편수."""

    @abstractmethod
    async def upsert_movie(self, command: MovieUpsertCommand) -> int:
        """slug 기준 insert 또는 update — movie.id 반환."""

    @abstractmethod
    async def list_all_slugs(self) -> list[tuple[int, str]]:
        """(movie.id, slug) 전체 목록 — credits 백필 순회 전용.

        list_movies()는 필터/정렬/페이지네이션이 있는 공개 조회용이라 배치 순회에
        오용하지 않기 위해 별도로 둔다.
        """
