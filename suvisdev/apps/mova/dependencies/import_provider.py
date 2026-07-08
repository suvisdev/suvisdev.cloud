"""영화 import DI."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.adapter.outbound.http.kofic_box_office_adapter import KoficBoxOfficeAdapter
from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapterError
from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter
from mova.adapter.outbound.pg.market_rankings_pg_repository import RankingsPgRepository
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
from mova.app.ports.input.import_use_case import ImportUseCase
from mova.app.ports.output.box_office_port import BoxOfficePort
from mova.app.ports.output.market_rankings_repository import RankingsRepositoryPort
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.ports.output.tmdb_catalog_port import TmdbCatalogPort
from mova.app.use_cases.import_interactor import ImportInteractor


def _build_import_interactor(session: AsyncSession) -> ImportInteractor:
    keymaker = get_keymaker()
    movies: MoviesRepositoryPort = MoviesPgRepository(session=session)
    rankings: RankingsRepositoryPort = RankingsPgRepository(session=session)
    catalog: TmdbCatalogPort = TmdbCatalogAdapter(keymaker.tmdb_api_key)
    box_office: BoxOfficePort = KoficBoxOfficeAdapter(keymaker.kofic_api_key)
    return ImportInteractor(
        movies=movies, catalog=catalog, rankings=rankings, box_office=box_office
    )


def get_import_use_case(
    db: AsyncSession = Depends(get_mova_db),
) -> ImportUseCase:
    return _build_import_interactor(db)


async def seed_catalog_if_sparse() -> object | None:
    """앱 startup용 — TMDB 키·DB 없으면 None."""
    keymaker = get_keymaker()
    if not keymaker.tmdb_api_key:
        return None

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory

    factory = get_mova_session_factory()
    async with factory() as session:
        try:
            return await _build_import_interactor(session).seed_catalog_if_sparse()
        except TmdbAdapterError:
            await session.rollback()
            raise
