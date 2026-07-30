from __future__ import annotations

import logging

from mova.app.dtos.studio_actors_dto import ActorUpsertCommand
from mova.app.dtos.studio_characters_dto import CharacterUpsertCommand
from mova.app.dtos.studio_import_dto import CreditsBackfillResultDto
from mova.app.dtos.studio_movie_directors_dto import MovieDirectorUpsertCommand
from mova.app.ports.input.credits_backfill_use_case import CreditsBackfillUseCase
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.ports.output.studio_actors_repository import ActorsRepositoryPort
from mova.app.ports.output.studio_characters_repository import CharactersRepositoryPort
from mova.app.ports.output.studio_movie_directors_repository import MovieDirectorsRepositoryPort
from mova.app.ports.output.tmdb_catalog_port import TmdbCatalogPort

logger = logging.getLogger(__name__)

_TMDB_SLUG_PREFIX = "tmdb-"


def _parse_tmdb_id(slug: str) -> int | None:
    """movies.slug는 tmdb_mapper.tmdb_slug()가 만든 'tmdb-{id}' 형식이라는 전제로 역파싱한다.

    이 전제가 깨지는 movie(수기 입력·비-TMDB 기원 등)가 생기면 이 함수는 None을
    반환하고, 호출부는 skipped로 집계하며 전체를 중단하지 않는다.
    """
    if not slug.startswith(_TMDB_SLUG_PREFIX):
        return None
    try:
        return int(slug[len(_TMDB_SLUG_PREFIX) :])
    except ValueError:
        return None


class CreditsBackfillInteractor(CreditsBackfillUseCase):
    def __init__(
        self,
        *,
        movies: MoviesRepositoryPort,
        catalog: TmdbCatalogPort,
        actors: ActorsRepositoryPort,
        characters: CharactersRepositoryPort,
        directors: MovieDirectorsRepositoryPort,
    ) -> None:
        self._movies = movies
        self._catalog = catalog
        self._actors = actors
        self._characters = characters
        self._directors = directors

    async def backfill_credits(self) -> CreditsBackfillResultDto:
        slugs = await self._movies.list_all_slugs()
        succeeded = 0
        failed = 0
        skipped = 0
        failed_slugs: list[str] = []

        for movie_id, slug in slugs:
            tmdb_id = _parse_tmdb_id(slug)
            if tmdb_id is None:
                skipped += 1
                logger.warning(
                    "[CreditsBackfillInteractor] slug 파싱 불가(tmdb- 접두사 아님), 스킵 | slug=%s",
                    slug,
                )
                continue

            try:
                await self._backfill_one(movie_id, tmdb_id)
                succeeded += 1
            except Exception:
                failed += 1
                failed_slugs.append(slug)
                logger.warning(
                    "[CreditsBackfillInteractor] credits 백필 실패, 다음 영화로 진행 | slug=%s",
                    slug,
                    exc_info=True,
                )

        logger.info(
            "[CreditsBackfillInteractor] 완료 succeeded=%d failed=%d skipped=%d",
            succeeded,
            failed,
            skipped,
        )
        return CreditsBackfillResultDto(
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            failed_slugs=failed_slugs,
        )

    async def _backfill_one(self, movie_id: int, tmdb_id: int) -> None:
        credits = await self._catalog.fetch_credits(tmdb_id)

        for member in credits.cast:
            actor_id = await self._actors.upsert_actor(
                ActorUpsertCommand(
                    tmdb_person_id=member.tmdb_person_id,
                    name=member.name,
                    role_type="actor",
                    profile_photo_url=member.profile_photo_url,
                )
            )
            await self._characters.upsert_character(
                CharacterUpsertCommand(
                    movie_id=movie_id,
                    actor_id=actor_id,
                    character_name=member.character,
                    billing_order=member.order,
                )
            )

        for director in credits.directors:
            actor_id = await self._actors.upsert_actor(
                ActorUpsertCommand(
                    tmdb_person_id=director.tmdb_person_id,
                    name=director.name,
                    role_type="director",
                    profile_photo_url=director.profile_photo_url,
                )
            )
            await self._directors.upsert_director(
                MovieDirectorUpsertCommand(movie_id=movie_id, actor_id=actor_id)
            )
