"""태그 Interactor — TagsUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.studio_tags_dto import TagGroupDto
from mova.app.ports.input.studio_tags_use_case import TagsUseCase
from mova.app.ports.output.studio_tags_repository import TagsRepositoryPort


class TagsInteractor(TagsUseCase):
    def __init__(self, repository: TagsRepositoryPort) -> None:
        self._repository = repository

    async def get_tags_by_movie(self, movie_id: int) -> TagGroupDto:
        return await self._repository.get_by_movie(movie_id)
