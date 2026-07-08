"""영화 Input Port — Router가 의존하는 추상 계약."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_movies_dto import MovieDetailDto, MovieFilterQuery, MovieListDto


class MoviesUseCase(ABC):
    @abstractmethod
    async def get_movie_detail(self, slug: str) -> MovieDetailDto | None:
        """영화 상세 조회. 없으면 None."""

    @abstractmethod
    async def list_movies(self, query: MovieFilterQuery) -> MovieListDto:
        """탐색형 필터 목록 조회."""
