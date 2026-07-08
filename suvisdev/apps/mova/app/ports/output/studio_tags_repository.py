"""태그 Output Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_tags_dto import TagGroupDto


class TagsRepositoryPort(ABC):
    @abstractmethod
    async def get_by_movie(self, movie_id: int) -> TagGroupDto:
        """영화 id로 태그 목록 조회 (kind별 그룹). 없으면 빈 그룹 반환."""
