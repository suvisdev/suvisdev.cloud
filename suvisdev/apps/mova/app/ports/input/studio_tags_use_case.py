"""태그 Input Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_tags_dto import TagGroupDto


class TagsUseCase(ABC):
    @abstractmethod
    async def get_tags_by_movie(self, movie_id: int) -> TagGroupDto:
        """영화 id로 태그 그룹 조회."""
