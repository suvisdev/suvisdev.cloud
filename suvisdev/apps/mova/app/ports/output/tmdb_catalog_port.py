"""TMDB 카탈로그 출력 포트 — 외부 영화 메타 조회."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_import_dto import TmdbCreditsDto, TmdbMovieSnapshotDto


class TmdbCatalogPort(ABC):
    @abstractmethod
    async def fetch_popular(self, *, page: int = 1) -> list[TmdbMovieSnapshotDto]:
        """TMDB /movie/popular 한 페이지."""

    @abstractmethod
    async def fetch_top_rated(self, *, page: int = 1) -> list[TmdbMovieSnapshotDto]:
        """TMDB /movie/top_rated 한 페이지."""

    @abstractmethod
    async def search(self, query: str, *, page: int = 1) -> list[TmdbMovieSnapshotDto]:
        """TMDB /search/movie."""

    @abstractmethod
    async def fetch_by_id(self, tmdb_id: int) -> TmdbMovieSnapshotDto:
        """TMDB /movie/{id} + credits."""

    @abstractmethod
    async def fetch_credits(self, tmdb_id: int) -> TmdbCreditsDto:
        """TMDB /movie/{id} + credits — cast/crew만 필요한 credits 백필 전용.

        fetch_by_id와 같은 엔드포인트를 호출하지만 리턴 타입이 다르다(영화
        스냅샷이 아니라 cast/crew). seed/import 경로가 쓰는 fetch_by_id는
        건드리지 않는다.
        """
