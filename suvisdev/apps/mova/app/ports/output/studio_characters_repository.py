"""영화↔배우 연결 Output Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_characters_dto import CastListDto


class CharactersRepositoryPort(ABC):
    @abstractmethod
    async def get_cast_by_movie(self, movie_id: int) -> CastListDto:
        """영화의 전체 출연진 (배우 정보 포함). 없으면 cast=[] 반환."""
