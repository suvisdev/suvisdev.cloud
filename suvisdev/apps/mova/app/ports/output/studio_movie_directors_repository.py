"""영화↔감독 연결 Output Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_movie_directors_dto import MovieDirectorUpsertCommand


class MovieDirectorsRepositoryPort(ABC):
    @abstractmethod
    async def upsert_director(self, command: MovieDirectorUpsertCommand) -> int:
        """(movie_id, actor_id) 기준 insert — 이미 있으면 그대로 두고 id 반환(멱등)."""
