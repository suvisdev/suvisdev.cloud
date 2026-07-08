"""TMDB 카탈로그 출력 포트 — 외부 영화 메타 조회."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_import_dto import TmdbMovieSnapshotDto


class TmdbCatalogPort(ABC):
    @abstractmethod
    async def fetch_popular(self, *, page: int = 1) -> list[TmdbMovieSnapshotDto]:
        """TMDB /movie/popular 한 페이지."""

    @abstractmethod
    async def search(self, query: str, *, page: int = 1) -> list[TmdbMovieSnapshotDto]:
        """TMDB /search/movie."""

    @abstractmethod
    async def fetch_by_id(self, tmdb_id: int) -> TmdbMovieSnapshotDto:
        """TMDB /movie/{id} + credits."""
