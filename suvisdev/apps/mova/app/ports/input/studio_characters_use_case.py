"""영화↔배우 연결 Input Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_characters_dto import CastListDto


class CharactersUseCase(ABC):
    @abstractmethod
    async def get_cast_by_movie(self, movie_id: int) -> CastListDto:
        """영화 id로 출연진 목록 조회."""
