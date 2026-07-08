"""영화↔배우 연결 PgRepository — CharactersRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.app.dtos.studio_characters_dto import CastListDto, CharacterWithActorDto
from mova.app.ports.output.studio_characters_repository import CharactersRepositoryPort

logger = logging.getLogger(__name__)


class CharactersPgRepository(CharactersRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_cast_by_movie(self, movie_id: int) -> CastListDto:
        rows = await self._session.execute(
            select(MovaCharacter, MovaActor)
            .join(MovaActor, MovaCharacter.actor_id == MovaActor.id)
            .where(MovaCharacter.movie_id == movie_id)
            .order_by(MovaActor.role_type, MovaActor.name)
        )
        pairs = rows.all()

        logger.debug("[CharactersPgRepository] movie_id=%d cast=%d", movie_id, len(pairs))
        return CastListDto(
            movie_id=movie_id,
            cast=[CharacterWithActorDto.from_orm(char, actor) for char, actor in pairs],
        )
