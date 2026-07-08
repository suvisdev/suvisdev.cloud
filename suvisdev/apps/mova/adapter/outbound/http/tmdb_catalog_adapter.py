"""TmdbCatalogPort 구현 — TMDB v3 HTTP."""

from __future__ import annotations

import logging

from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter
from mova.adapter.outbound.http.tmdb_mapper import map_tmdb_row
from mova.app.dtos.studio_import_dto import TmdbMovieSnapshotDto
from mova.app.ports.output.tmdb_catalog_port import TmdbCatalogPort

logger = logging.getLogger(__name__)


class TmdbCatalogAdapter(TmdbCatalogPort):
    def __init__(self, api_key: str, *, language: str = "ko-KR") -> None:
        self._client = TmdbAdapter(api_key, language=language)
        self._genre_map: dict[int, str] | None = None

    async def _genres(self) -> dict[int, str]:
        if self._genre_map is None:
            self._genre_map = await self._client.genre_map()
        return self._genre_map

    async def fetch_popular(self, *, page: int = 1) -> list[TmdbMovieSnapshotDto]:
        genre_map = await self._genres()
        rows = await self._client.fetch_popular(page=page)
        snapshots: list[TmdbMovieSnapshotDto] = []
        for row in rows:
            poster = self._client.poster_url(str(row.get("poster_path") or ""))
            mapped = map_tmdb_row(row, genre_map=genre_map, poster_url=poster)
            if mapped:
                snapshots.append(mapped)
        logger.debug("[TmdbCatalogAdapter] fetch_popular page=%d count=%d", page, len(snapshots))
        return snapshots

    async def search(self, query: str, *, page: int = 1) -> list[TmdbMovieSnapshotDto]:
        genre_map = await self._genres()
        rows = await self._client.search_movies(query, page=page)
        snapshots: list[TmdbMovieSnapshotDto] = []
        for row in rows:
            poster = self._client.poster_url(str(row.get("poster_path") or ""))
            mapped = map_tmdb_row(row, genre_map=genre_map, poster_url=poster)
            if mapped:
                snapshots.append(mapped)
        logger.debug("[TmdbCatalogAdapter] search q=%r count=%d", query, len(snapshots))
        return snapshots

    async def fetch_by_id(self, tmdb_id: int) -> TmdbMovieSnapshotDto:
        genre_map = await self._genres()
        row = await self._client.fetch_movie_detail(tmdb_id)
        poster = self._client.poster_url(str(row.get("poster_path") or ""))
        mapped = map_tmdb_row(row, genre_map=genre_map, poster_url=poster)
        if mapped is None:
            msg = f"TMDB movie {tmdb_id} mapping failed"
            raise ValueError(msg)
        if not mapped.genres and row.get("genres"):
            from mova.adapter.outbound.http.tmdb_mapper import map_genre_objects

            mapped = TmdbMovieSnapshotDto(
                tmdb_id=mapped.tmdb_id,
                slug=mapped.slug,
                title=mapped.title,
                release_year=mapped.release_year,
                rating=mapped.rating,
                poster_url=mapped.poster_url,
                genres=map_genre_objects(list(row.get("genres") or [])),
            )
        return mapped
