"""영화↔배우 연결 Interactor — CharactersUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.studio_characters_dto import CastListDto
from mova.app.ports.input.studio_characters_use_case import CharactersUseCase
from mova.app.ports.output.studio_characters_repository import CharactersRepositoryPort


class CharactersInteractor(CharactersUseCase):
    def __init__(self, repository: CharactersRepositoryPort) -> None:
        self._repository = repository

    async def get_cast_by_movie(self, movie_id: int) -> CastListDto:
        return await self._repository.get_cast_by_movie(movie_id)
