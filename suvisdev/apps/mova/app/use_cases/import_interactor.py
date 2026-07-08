from __future__ import annotations

import logging
from datetime import date

from mova.app.dtos.market_box_office_dto import BoxOfficeEntryDto, KoficImportCommand
from mova.app.dtos.studio_import_dto import (
    MovieImportResultDto,
    MovieUpsertCommand,
    StudioImportQuery,
    StudioImportResponse,
    TmdbImportCommand,
    TmdbMovieSnapshotDto,
)
from mova.app.ports.input.import_use_case import ImportUseCase
from mova.app.ports.output.box_office_port import BoxOfficePort
from mova.app.ports.output.market_rankings_repository import RankingsRepositoryPort
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.ports.output.tmdb_catalog_port import TmdbCatalogPort

logger = logging.getLogger(__name__)

MIN_CATALOG_MOVIES = 5
SEED_POPULAR_PAGES = 2
SEED_RANKING_LIMIT = 10
SEARCH_IMPORT_LIMIT = 5


class ImportInteractor(ImportUseCase):
    def __init__(
        self,
        movies: MoviesRepositoryPort,
        catalog: TmdbCatalogPort,
        rankings: RankingsRepositoryPort,
        box_office: BoxOfficePort,
    ) -> None:
        self._movies = movies
        self._catalog = catalog
        self._rankings = rankings
        self._box_office = box_office

    async def introduce_myself(self, query: StudioImportQuery) -> StudioImportResponse:
        return StudioImportResponse(id=query.id, name=query.name)

    async def seed_catalog_if_sparse(self) -> MovieImportResultDto:
        count = await self._movies.count_movies()
        if count >= MIN_CATALOG_MOVIES:
            return MovieImportResultDto(
                imported=0,
                message=f"카탈로그 {count}편 — 시드 생략 (기준 {MIN_CATALOG_MOVIES}편)",
            )
        snapshots: list[TmdbMovieSnapshotDto] = []
        for page in range(1, SEED_POPULAR_PAGES + 1):
            snapshots.extend(await self._catalog.fetch_popular(page=page))
        return await self._persist_snapshots(snapshots, update_rankings=True)

    async def import_tmdb(self, command: TmdbImportCommand) -> MovieImportResultDto:
        snapshots = await self._resolve_snapshots(command)
        return await self._persist_snapshots(snapshots, update_rankings=False)

    async def import_kofic_boxoffice(self, command: KoficImportCommand) -> MovieImportResultDto:
        entries = await self._box_office.fetch_box_office(command.target_date, command.week_gb)
        if not entries:
            return MovieImportResultDto(imported=0, message="KOFIC 박스오피스 결과가 없습니다.")

        # KOFIC 순위 순서를 유지하며 매칭된 movie.id만 수집 (미매칭은 순위 압축).
        ranked_ids: list[int] = []
        for entry in entries:
            movie_id = await self._resolve_box_office_movie(entry)
            if movie_id is not None:
                ranked_ids.append(movie_id)

        if not ranked_ids:
            return MovieImportResultDto(
                imported=0, message="KOFIC 박스오피스와 매칭되는 작품이 없습니다."
            )

        saved = await self._rankings.save_box_office_ranking(ranked_ids, date.today())
        logger.info(
            "[ImportInteractor] kofic box_office matched=%d saved=%d", len(ranked_ids), saved
        )
        return MovieImportResultDto(
            imported=len(ranked_ids),
            movie_ids=ranked_ids,
            rankings_updated=saved > 0,
            message=f"KOFIC 박스오피스 {len(ranked_ids)}편 반영",
        )

    async def _resolve_box_office_movie(self, entry: BoxOfficeEntryDto) -> int | None:
        """카탈로그에 있으면 그 id, 없으면 TMDB 검색으로 enrich 후 upsert. 둘 다 실패 시 None."""
        existing = await self._movies.find_by_title(entry.title)
        if existing is not None:
            return existing.id
        snapshots = await self._catalog.search(entry.title, page=1)
        if not snapshots:
            return None
        return await self._movies.upsert_movie(self._to_upsert(snapshots[0]))

    async def _persist_snapshots(
        self,
        snapshots: list[TmdbMovieSnapshotDto],
        *,
        update_rankings: bool,
    ) -> MovieImportResultDto:
        if not snapshots:
            return MovieImportResultDto(imported=0, message="가져올 TMDB 작품이 없습니다.")

        pairs: list[tuple[int, TmdbMovieSnapshotDto]] = []
        for snap in snapshots:
            movie_id = await self._movies.upsert_movie(self._to_upsert(snap))
            pairs.append((movie_id, snap))

        rankings_updated = False
        if update_rankings and pairs:
            ranked_ids = [
                movie_id
                for movie_id, _ in sorted(pairs, key=lambda pair: pair[1].rating, reverse=True)[
                    :SEED_RANKING_LIMIT
                ]
            ]
            saved = await self._rankings.save_box_office_ranking(ranked_ids, date.today())
            rankings_updated = saved > 0

        movie_ids = [movie_id for movie_id, _ in pairs]
        logger.info(
            "[ImportInteractor] persisted=%d rankings=%s",
            len(movie_ids),
            rankings_updated,
        )
        return MovieImportResultDto(
            imported=len(movie_ids),
            movie_ids=movie_ids,
            rankings_updated=rankings_updated,
            message=f"TMDB에서 {len(movie_ids)}편 반영",
        )

    async def _resolve_snapshots(self, command: TmdbImportCommand) -> list[TmdbMovieSnapshotDto]:
        if command.tmdb_id is not None:
            return [await self._catalog.fetch_by_id(command.tmdb_id)]

        if command.query and command.query.strip():
            found = await self._catalog.search(command.query.strip(), page=1)
            return found[:SEARCH_IMPORT_LIMIT]

        pages = max(0, command.popular_pages)
        if pages > 0:
            snapshots: list[TmdbMovieSnapshotDto] = []
            for page in range(1, pages + 1):
                snapshots.extend(await self._catalog.fetch_popular(page=page))
            return snapshots

        return []

    @staticmethod
    def _to_upsert(snap: TmdbMovieSnapshotDto) -> MovieUpsertCommand:
        return MovieUpsertCommand(
            slug=snap.slug,
            title=snap.title,
            release_year=snap.release_year,
            rating=snap.rating,
            poster_url=snap.poster_url,
            genres=snap.genres,
        )
