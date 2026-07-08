"""영화 Interactor — MoviesUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.studio_movies_dto import MovieDetailDto, MovieFilterQuery, MovieListDto
from mova.app.ports.input.studio_movies_use_case import MoviesUseCase
from mova.app.ports.output.movies_repository import MoviesRepositoryPort


class MoviesInteractor(MoviesUseCase):
    def __init__(self, repository: MoviesRepositoryPort) -> None:
        self._repository = repository

    async def get_movie_detail(self, slug: str) -> MovieDetailDto | None:
        return await self._repository.get_by_slug(slug)

    async def list_movies(self, query: MovieFilterQuery) -> MovieListDto:
        return await self._repository.list_movies(query)
