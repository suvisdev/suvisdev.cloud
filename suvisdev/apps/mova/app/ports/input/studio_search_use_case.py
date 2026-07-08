"""검색 입력 포트 — 영화 검색 유스케이스 계약."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_search_dto import SearchResultDto


class SearchUseCase(ABC):
    @abstractmethod
    async def search_movies(self, q: str, limit: int, offset: int) -> SearchResultDto:
        pass
