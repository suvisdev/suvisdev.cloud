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
from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase

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
        hub_rag: HubRagUseCase,
    ) -> None:
        self._movies = movies
        self._catalog = catalog
        self._rankings = rankings
        self._box_office = box_office
        self._hub_rag = hub_rag

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
        snap = snapshots[0]
        movie_id = await self._movies.upsert_movie(self._to_upsert(snap))
        await self._ingest_to_hub(snap, movie_id)
        return movie_id

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
            await self._ingest_to_hub(snap, movie_id)

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

        popular_pages = max(0, command.popular_pages)
        if popular_pages > 0:
            snapshots: list[TmdbMovieSnapshotDto] = []
            for page in range(1, popular_pages + 1):
                snapshots.extend(await self._catalog.fetch_popular(page=page))
            return snapshots

        top_rated_pages = max(0, command.top_rated_pages)
        if top_rated_pages > 0:
            snapshots = []
            for page in range(1, top_rated_pages + 1):
                snapshots.extend(await self._catalog.fetch_top_rated(page=page))
            return snapshots

        return []

    async def _ingest_to_hub(self, snap: TmdbMovieSnapshotDto, movie_id: int) -> None:
        """TMDB/KOFIC로 확보한 영화 정보를 ontology Hub의 RAG 지식 저장소에 반영한다.

        임베딩·색인 실패가 임포트 자체를 막지 않도록 격리한다(원본 카탈로그 upsert는 이미 완료됨).

        `source_ref`는 반드시 `movie.id` — 채팅이 이 값을 movie_id로 int() 파싱해
        후보 집합을 만든다(chat_reply.enrich_from_db). slug를 넣으면 파싱이 조용히
        실패해 추천이 전부 드롭된다.
        """
        content_lines = [snap.overview]
        if snap.genres:
            content_lines.append(f"장르: {', '.join(snap.genres)}")
        if snap.cast:
            content_lines.append(f"출연: {', '.join(snap.cast)}")
        content = "\n".join(line for line in content_lines if line)
        try:
            await self._hub_rag.ingest_movie(
                HubKnowledgeUpsertCommand(
                    source="mova_movie",
                    source_ref=str(movie_id),
                    title=snap.title,
                    content=content,
                )
            )
        except Exception:
            logger.warning(
                "[ImportInteractor] hub_rag ingest 실패, 카탈로그 임포트는 유지 | slug=%s",
                snap.slug,
                exc_info=True,
            )

    @staticmethod
    def _to_upsert(snap: TmdbMovieSnapshotDto) -> MovieUpsertCommand:
        return MovieUpsertCommand(
            slug=snap.slug,
            title=snap.title,
            release_year=snap.release_year,
            rating=snap.rating,
            poster_url=snap.poster_url,
            genres=snap.genres,
            synopsis=snap.overview,
            original_language=snap.original_language,
        )
