"""영화 Output Port — PgRepository가 구현한다."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_import_dto import MovieUpsertCommand
from mova.app.dtos.studio_movies_dto import (
    MovieDetailDto,
    MovieFilterQuery,
    MovieListDto,
    MovieListItemDto,
)


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
    async def list_missing_synopsis(self, limit: int | None) -> list[tuple[int, str]]:
        """synopsis가 비어 있는 TMDB 원산 영화 (movie.id, slug) — synopsis 백필 순회 전용."""

    @abstractmethod
    async def update_synopsis(self, movie_id: int, synopsis: str) -> None:
        """movie_id의 synopsis만 갱신."""

    @abstractmethod
    async def list_missing_original_language(self, limit: int | None) -> list[tuple[int, str]]:
        """original_language가 비어 있는 TMDB 원산 영화 (movie.id, slug) — 백필 순회 전용."""

    @abstractmethod
    async def update_original_language(self, movie_id: int, original_language: str) -> None:
        """movie_id의 original_language만 갱신."""

    @abstractmethod
    async def list_missing_origin_country(self, limit: int | None) -> list[tuple[int, str]]:
        """origin_country가 비어 있는 TMDB 원산 영화 (movie.id, slug) — 백필 순회 전용."""

    @abstractmethod
    async def update_origin_country(self, movie_id: int, origin_country: list[str]) -> None:
        """movie_id의 origin_country만 갱신."""

    @abstractmethod
    async def list_missing_age_rating_or_platforms(
        self, limit: int | None
    ) -> list[tuple[int, str]]:
        """age_rating·platforms가 둘 다 미백필(NULL/[])인 TMDB 원산 영화 — 백필 순회 전용."""

    @abstractmethod
    async def update_age_rating_and_platforms(
        self, movie_id: int, age_rating: str | None, platforms: list[dict[str, str | None]]
    ) -> None:
        """movie_id의 age_rating·platforms만 갱신."""

    @abstractmethod
    async def list_missing_trailer(self, limit: int | None) -> list[tuple[int, str]]:
        """trailer_key가 NULL인 TMDB 원산 영화 (movie.id, slug) — 백필 순회 전용."""

    @abstractmethod
    async def update_trailer_key(self, movie_id: int, trailer_key: str | None) -> None:
        """movie_id의 trailer_key만 갱신."""

    @abstractmethod
    async def list_missing_embedding(self, limit: int | None) -> list[tuple[int, str]]:
        """embedding이 NULL인 영화 (movie.id, slug) — 유사도 임베딩 백필 순회 전용."""

    @abstractmethod
    async def update_embedding(self, movie_id: int, embedding: list[float]) -> None:
        """movie_id의 embedding만 갱신."""

    @abstractmethod
    async def list_embeddings_by_ids(self, movie_ids: list[int]) -> dict[int, list[float]]:
        """movie_id 리스트에 대응하는 embedding 매핑 — 채팅 추천 재정렬 전용.

        embedding이 NULL인 항목은 반환 dict에서 제외한다(빈 dict일 수 있음).
        입력이 빈 리스트면 빈 dict 즉시 반환. 재정렬 경로에서 자기 자신
        cosine을 계산하는 게 아니라 taste vector와 비교하므로 slug 대신
        movie_id 배치 조회 형태로 설계.
        """

    @abstractmethod
    async def find_similar_movies(self, slug: str, limit: int) -> list[MovieListItemDto] | None:
        """slug 영화의 embedding과 코사인 거리가 가까운 순 — 자기 자신은 제외.

        영화가 없거나 embedding이 아직 없으면 None(0건 리스트와 구분 — 전자는
        "말할 수 없음", 후자는 "물어봤지만 비슷한 게 없음").
        """

    @abstractmethod
    async def list_all_slugs(self) -> list[tuple[int, str]]:
        """(movie.id, slug) 전체 목록 — credits 백필 순회 전용.

        list_movies()는 필터/정렬/페이지네이션이 있는 공개 조회용이라 배치 순회에
        오용하지 않기 위해 별도로 둔다.
        """
