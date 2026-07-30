"""TMDB credits 백필 DI — 수동 실행 스크립트 전용(어드민 엔드포인트·스케줄러 미배선)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
from mova.adapter.outbound.pg.studio_actors_pg_repository import ActorsPgRepository
from mova.adapter.outbound.pg.studio_characters_pg_repository import CharactersPgRepository
from mova.adapter.outbound.pg.studio_movie_directors_pg_repository import (
    MovieDirectorsPgRepository,
)
from mova.app.dtos.studio_import_dto import CreditsBackfillResultDto
from mova.app.use_cases.credits_backfill_interactor import CreditsBackfillInteractor


def _build_credits_backfill_interactor(session: AsyncSession) -> CreditsBackfillInteractor:
    keymaker = get_keymaker()
    return CreditsBackfillInteractor(
        movies=MoviesPgRepository(session=session),
        catalog=TmdbCatalogAdapter(keymaker.tmdb_api_key),
        actors=ActorsPgRepository(session=session),
        characters=CharactersPgRepository(session=session),
        directors=MovieDirectorsPgRepository(session=session),
    )


async def backfill_credits() -> CreditsBackfillResultDto:
    """스크립트 전용 진입점 — FastAPI 요청 컨텍스트 없이 직접 세션을 연다(seed_catalog_if_sparse와 동일 패턴)."""
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory

    factory = get_mova_session_factory()
    async with factory() as session:
        return await _build_credits_backfill_interactor(session).backfill_credits()
