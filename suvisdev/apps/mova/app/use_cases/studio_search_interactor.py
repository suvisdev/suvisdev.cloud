"""검색 Interactor — SearchUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.studio_search_dto import SearchResultDto
from mova.app.ports.input.studio_search_use_case import SearchUseCase
from mova.app.ports.output.studio_search_repository import SearchRepositoryPort


class SearchInteractor(SearchUseCase):
    def __init__(self, repository: SearchRepositoryPort) -> None:
        self._repository = repository

    async def search_movies(self, q: str, limit: int, offset: int) -> SearchResultDto:
        return await self._repository.search_by_label(q, limit, offset)
